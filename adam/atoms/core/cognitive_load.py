# =============================================================================
# ADAM Cognitive Load Atom
# Location: adam/atoms/core/cognitive_load.py
# =============================================================================

"""
COGNITIVE LOAD ATOM

Grounded in Cognitive Load Theory (Sweller, 1988) and Working Memory
research (Baddeley, 1986). Models the user's available cognitive
processing capacity and matches mechanism complexity to available
bandwidth.

Key insight: When cognitive load is HIGH (busy, stressed, multitasking),
complex mechanisms fail. Users default to heuristic processing (System 1).
When load is LOW (relaxed, focused), users can engage with complex
arguments and sophisticated framing. This atom estimates cognitive load
and selects mechanism complexity accordingly — the same person at different
cognitive loads needs DIFFERENT mechanisms.

Academic Foundation:
- Sweller (1988): Cognitive Load Theory
- Baddeley (1986): Working Memory Model
- Kahneman (2011): Thinking, Fast and Slow — System 1 vs System 2
- Petty & Cacioppo (1986): ELM — elaboration depends on available capacity
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


# Mechanism complexity: how much cognitive effort each requires
MECHANISM_COMPLEXITY = {
    # System 1 (low complexity — works under high load)
    "social_proof": 0.15,        # "Others chose this" — instant
    "scarcity": 0.2,             # "Running out" — visceral
    "attention_dynamics": 0.15,  # Salience — automatic
    "embodied_cognition": 0.1,   # Sensory — pre-cognitive
    "mimetic_desire": 0.25,      # Imitation — instinctive
    "unity": 0.2,                # Belonging — automatic
    # System 2 (high complexity — needs low load)
    "authority": 0.5,            # Evaluating expertise
    "anchoring": 0.55,           # Price comparison
    "commitment": 0.6,           # Evaluating long-term value
    "identity_construction": 0.5, # Self-concept processing
    "regulatory_focus": 0.55,    # Gain/loss evaluation
    "temporal_construal": 0.6,   # Abstract/concrete processing
    "reciprocity": 0.4,          # Social exchange calculation
    "storytelling": 0.35,        # Narrative processing
}

# Cognitive load → mechanism strategy
LOAD_STRATEGIES = {
    "high_load": {
        "description": "Overloaded — use System 1 heuristics only",
        "max_complexity": 0.3,
        "mechanism_boosts": {
            "social_proof": 0.2,
            "scarcity": 0.15,
            "embodied_cognition": 0.15,
            "attention_dynamics": 0.1,
        },
        "mechanism_penalties": {
            "commitment": -0.15,
            "temporal_construal": -0.15,
            "anchoring": -0.1,
            "authority": -0.1,
        },
    },
    "moderate_load": {
        "description": "Some capacity — mix of heuristics and central processing",
        "max_complexity": 0.55,
        "mechanism_boosts": {
            "social_proof": 0.1,
            "identity_construction": 0.1,
            "mimetic_desire": 0.05,
            "reciprocity": 0.05,
        },
        "mechanism_penalties": {
            "temporal_construal": -0.05,
        },
    },
    "low_load": {
        "description": "Full capacity — can process complex arguments",
        "max_complexity": 0.9,
        "mechanism_boosts": {
            "authority": 0.15,
            "commitment": 0.1,
            "identity_construction": 0.1,
            "anchoring": 0.1,
            "temporal_construal": 0.1,
        },
        "mechanism_penalties": {
            "attention_dynamics": -0.05,  # Salience tricks less needed
        },
    },
}


class CognitiveLoadAtom(BaseAtom):
    """
    Estimates cognitive load and matches mechanism complexity to capacity.

    This atom:
    1. Estimates current cognitive load from NDF + context
    2. Classifies processing capacity (high/moderate/low load)
    3. Filters mechanisms by complexity (only use what the user can process)
    4. Adjusts System 1 vs System 2 mechanism balance
    """

    ATOM_TYPE = AtomType.COGNITIVE_LOAD
    ATOM_NAME = "cognitive_load"
    TARGET_CONSTRUCT = "processing_capacity"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _estimate_cognitive_load(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate current cognitive load.

        From NDF:
        - cognitive_engagement: HIGH → currently processing (higher load)
        - arousal_seeking: HIGH + context → overstimulated (higher load)
        - uncertainty_tolerance: LOW → more cognitive effort to decide

        From context:
        - Time of day (evening = higher load)
        - Mobile vs desktop (mobile = higher load)
        - Multi-tasking signals
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        load = 0.5

        if psy.has_any:
            ce = psy.cognitive_engagement
            aas = psy.arousal_seeking
            ut = psy.uncertainty_tolerance

            # Paradox: high CE means they CAN think, but may already be loaded
            # Use approach_avoidance as tiebreaker
            aa = psy.approach_avoidance

            load = (
                0.3 +
                ce * 0.15 +          # Engaged mind → somewhat loaded
                (1 - ut) * 0.2 +     # Intolerant → more effort per decision
                aas * 0.1            # High arousal → sensory load
            )

        # Context modifiers
        is_mobile = ad_context.get("is_mobile", False)
        if is_mobile:
            load = min(0.95, load + 0.15)  # Mobile = higher load

        from datetime import datetime
        hour = datetime.now().hour
        if hour >= 20 or hour <= 6:
            load = min(0.95, load + 0.1)   # Evening/night = fatigued

        num_ads_seen = ad_context.get("ads_seen_session", 0)
        if num_ads_seen > 5:
            load = min(0.95, load + 0.1)   # Ad fatigue

        load = max(0.1, min(0.95, load))

        # Available capacity is inverse of load
        capacity = 1.0 - load

        if load > 0.65:
            level = "high_load"
        elif load > 0.35:
            level = "moderate_load"
        else:
            level = "low_load"

        return {
            "cognitive_load": load,
            "available_capacity": capacity,
            "level": level,
            "processing_mode": "heuristic" if load > 0.6 else ("systematic" if load < 0.35 else "mixed"),
        }

    def _compute_mechanism_adjustments(
        self,
        load_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert cognitive load to mechanism adjustments."""
        level = load_profile["level"]
        max_complexity = LOAD_STRATEGIES[level]["max_complexity"]

        adjustments = {}

        # Apply strategy boosts/penalties
        strategy = LOAD_STRATEGIES[level]
        for mech, adj in strategy["mechanism_boosts"].items():
            adjustments[mech] = adj
        for mech, adj in strategy["mechanism_penalties"].items():
            adjustments[mech] = adj

        # Additional: penalize ALL mechanisms above complexity threshold
        for mech, complexity in MECHANISM_COMPLEXITY.items():
            if complexity > max_complexity and mech not in adjustments:
                penalty = -(complexity - max_complexity) * 0.3
                adjustments[mech] = adjustments.get(mech, 0) + penalty

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build cognitive load output."""

        profile = self._estimate_cognitive_load(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        primary = profile["level"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.8, 0.4 + abs(profile["cognitive_load"] - 0.5) * 0.6)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "load_profile": profile,
                "mechanism_adjustments": adjustments,
                "processing_guidance": {
                    "max_message_complexity": LOAD_STRATEGIES[profile["level"]]["max_complexity"],
                    "use_heuristics": profile["processing_mode"] == "heuristic",
                    "use_arguments": profile["processing_mode"] == "systematic",
                    "keep_simple": profile["cognitive_load"] > 0.6,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "cognitive_load": profile["cognitive_load"],
                "available_capacity": profile["available_capacity"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
