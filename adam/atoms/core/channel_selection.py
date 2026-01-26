# =============================================================================
# ADAM Channel Selection Atom
# Location: adam/atoms/core/channel_selection.py
# =============================================================================

"""
CHANNEL SELECTION ATOM

Selects optimal advertising channels (shows, podcasts, stations) based on
psycholinguistic matching between customer profile and channel profiles.

Receives:
- Customer psychological profile (from upstream atoms)
- Mechanism selections (what persuasion approach to use)
- Product/brand context

Outputs:
- Ranked channel recommendations
- Psycholinguistic match scores
- Synergy explanations
- Optimal time slots

This atom integrates with the iHeart psycholinguistic graph database.
"""

import logging
from typing import Dict, List, Optional, Any

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    FusionResult,
    MultiSourceEvidence,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

logger = logging.getLogger(__name__)


# Map archetypes to target emotional states
ARCHETYPE_EMOTION_MAPPING = {
    "achiever": ["excitement", "anticipation", "inspiration", "admiration"],
    "explorer": ["curiosity", "excitement", "anticipation", "amusement"],
    "guardian": ["trust", "contentment", "nostalgia", "belonging"],
    "connector": ["connection", "joy", "belonging", "empathy"],
    "pragmatist": ["trust", "contentment", "curiosity"],
}

# Map archetypes to target personality traits
ARCHETYPE_TRAIT_MAPPING = {
    "achiever": ["conscientiousness_high", "need_for_cognition", "self_monitoring"],
    "explorer": ["openness_high", "sensation_seeking", "extraversion_high"],
    "guardian": ["conscientiousness_high", "agreeableness_high", "neuroticism_high"],
    "connector": ["extraversion_high", "agreeableness_high", "need_for_affect"],
    "pragmatist": ["conscientiousness_high", "need_for_cognition"],
}

# Map mechanisms to persuasion techniques
MECHANISM_TO_TECHNIQUE = {
    "authority": ["authority", "rational_argument"],
    "social_proof": ["social_proof", "unity"],
    "scarcity": ["scarcity", "fear_appeal"],
    "reciprocity": ["reciprocity", "liking"],
    "commitment": ["commitment_consistency"],
    "identity_construction": ["aspiration", "unity"],
    "mimetic_desire": ["social_proof", "aspiration"],
    "temporal_construal": ["storytelling", "nostalgia"],
}


class ChannelSelectionAtom(BaseAtom):
    """
    Atom for selecting optimal advertising channels.
    
    Uses psycholinguistic matching to find shows/podcasts that:
    1. Evoke emotions aligned with customer archetype
    2. Attract personality traits matching target segment
    3. Are receptive to selected persuasion mechanisms
    4. Air at optimal times for engagement
    """
    
    ATOM_TYPE = AtomType.CHANNEL_SELECTION
    ATOM_NAME = "channel_selection"
    TARGET_CONSTRUCT = "channel_recommendation"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,  # Neo4j iHeart data
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.BANDIT_POSTERIORS,  # Learning from past placements
    ]
    
    def __init__(self, **kwargs):
        """Initialize with graph intelligence service."""
        super().__init__(**kwargs)
        self._graph_intelligence = None
    
    async def _get_graph_intelligence(self):
        """Lazy load graph intelligence service."""
        if self._graph_intelligence is None:
            from adam.orchestrator.graph_intelligence import get_graph_intelligence
            self._graph_intelligence = get_graph_intelligence()
        return self._graph_intelligence
    
    def _get_upstream_context(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Extract relevant context from upstream atoms."""
        context = {
            "archetype": "pragmatist",
            "mechanisms": [],
            "regulatory_focus": "balanced",
        }
        
        # Get personality assessment
        personality_output = atom_input.get_upstream("atom_personality_expression")
        if personality_output:
            # AtomOutput has primary_assessment and secondary_assessments
            context["archetype"] = personality_output.primary_assessment or "pragmatist"
            # Check secondary_assessments for more detail
            if personality_output.secondary_assessments:
                context["archetype"] = personality_output.secondary_assessments.get(
                    "primary_archetype", context["archetype"]
                )
        
        # Get mechanism selection
        mechanism_output = atom_input.get_upstream("atom_mechanism_activation")
        if mechanism_output:
            context["mechanisms"] = mechanism_output.recommended_mechanisms or []
        
        # Get regulatory focus
        regulatory_output = atom_input.get_upstream("atom_regulatory_focus")
        if regulatory_output:
            context["regulatory_focus"] = regulatory_output.primary_assessment or "balanced"
        
        return context
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query iHeart psycholinguistic data from Neo4j."""
        
        if source == IntelligenceSourceType.GRAPH_EMERGENCE:
            return await self._query_channel_matches(atom_input)
        
        return None
    
    async def _query_channel_matches(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query Neo4j for channel matches based on psychological profile.
        """
        graph_intel = await self._get_graph_intelligence()
        
        # Extract context from upstream atoms
        context = self._get_upstream_context(atom_input)
        archetype = context["archetype"].lower()
        mechanisms = context["mechanisms"]
        
        # Map archetype to target emotions and traits
        target_emotions = ARCHETYPE_EMOTION_MAPPING.get(
            archetype, ["trust", "contentment"]
        )
        target_traits = ARCHETYPE_TRAIT_MAPPING.get(
            archetype, ["conscientiousness_high"]
        )
        
        # Map mechanisms to persuasion techniques
        persuasion_techniques = []
        for mech in mechanisms:
            mech_key = mech.lower().replace(" ", "_")
            techniques = MECHANISM_TO_TECHNIQUE.get(mech_key, [])
            persuasion_techniques.extend(techniques)
        
        # Query Neo4j for matching shows
        try:
            shows = await graph_intel.get_matching_shows(
                target_emotions=target_emotions,
                target_traits=target_traits,
                persuasion_techniques=persuasion_techniques,
                min_score=0.3,
                limit=15
            )
            
            if not shows:
                logger.warning("No matching shows found for profile")
                return None
            
            # Calculate overall match quality
            avg_score = sum(s.get("total_score", 0) for s in shows) / len(shows) if shows else 0
            
            # Build evidence
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                construct=self.TARGET_CONSTRUCT,
                assessment=f"Found {len(shows)} matching channels",
                assessment_value=avg_score,
                confidence=min(0.9, 0.5 + len(shows) * 0.03),  # More matches = more confidence
                confidence_semantics=ConfidenceSemantics.GRAPH_COVERAGE,
                strength=EvidenceStrength.STRONG if len(shows) >= 5 else EvidenceStrength.MODERATE,
                support_count=len(shows),
                reasoning=f"Matched {len(shows)} shows/podcasts for {archetype} archetype",
                raw_data={
                    "shows": shows,
                    "target_emotions": target_emotions,
                    "target_traits": target_traits,
                    "persuasion_techniques": persuasion_techniques,
                    "archetype": archetype,
                },
            )
            
        except Exception as e:
            logger.error(f"Error querying channel matches: {e}")
            return None
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """
        Build channel selection output from fused evidence.
        """
        # Get upstream context
        context = self._get_upstream_context(atom_input)
        archetype = context["archetype"]
        mechanisms = context["mechanisms"]
        
        # Extract shows from graph evidence
        shows = []
        podcasts = []
        target_emotions = []
        target_traits = []
        
        graph_evidence = evidence.evidence.get(IntelligenceSourceType.GRAPH_EMERGENCE)
        if graph_evidence and graph_evidence.raw_data:
            raw = graph_evidence.raw_data
            all_shows = raw.get("shows", [])
            target_emotions = raw.get("target_emotions", [])
            target_traits = raw.get("target_traits", [])
            
            # Separate shows and podcasts
            for s in all_shows:
                if s.get("show_type") == "podcast":
                    podcasts.append(s)
                else:
                    shows.append(s)
        
        # Build reasoning
        reasoning_parts = []
        if shows:
            best = shows[0]
            reasoning_parts.append(
                f"Top show '{best.get('show_name')}' matches {archetype} archetype "
                f"with score {best.get('total_score', 0):.2f}"
            )
        if mechanisms:
            reasoning_parts.append(
                f"Optimized for mechanisms: {', '.join(mechanisms[:3])}"
            )
        
        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Channel selection based on psychological profile"
        
        # Build output
        output = AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=f"{len(shows) + len(podcasts)} channels selected",
            assessment_value=fusion_result.confidence,
            secondary_assessments={
                "recommended_shows": shows[:5],
                "recommended_podcasts": podcasts[:5],
                "target_emotions": target_emotions,
                "target_traits": target_traits,
                "archetype": archetype,
                "mechanisms": mechanisms,
                "channel_reasoning": reasoning,
            },
            recommended_mechanisms=mechanisms,
            inferred_states={
                "channel_match_quality": fusion_result.confidence,
                "shows_found": len(shows),
                "podcasts_found": len(podcasts),
            },
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
        )
        
        return output
