# =============================================================================
# ADAM BrandPersonalityAtom
# Location: adam/atoms/core/brand_personality.py
# =============================================================================

"""
BRAND PERSONALITY ATOM

Level 2 atom that injects brand personality as evidence into the DAG.

This atom:
1. Retrieves brand personality profile from Neo4j
2. Computes brand-consumer archetype compatibility
3. Identifies optimal mechanisms for this brand personality
4. Provides brand voice characteristics for copy generation
5. Emits learning signals for brand effectiveness

The Brand Personality is a CORE PRIMITIVE in ADAM - it influences:
- Mechanism selection (which psychological levers work for this brand)
- Station matching (brand voice → station persona fit)
- Copy generation (brand voice characteristics)
- Archetype targeting (which consumer archetypes are attracted)

Psychological Foundation:
- Aaker (1997) Brand Personality Framework
- Mark & Pearson (2001) Brand Archetypes
- Fournier (1998) Consumer-Brand Relationships
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

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

logger = logging.getLogger(__name__)


# =============================================================================
# BRAND PERSONALITY MODELS
# =============================================================================

class BrandPersonalityEvidence(BaseModel):
    """Evidence from brand personality analysis."""
    
    brand_id: str
    brand_name: str
    
    # Archetype
    brand_archetype: str
    brand_archetype_confidence: float = Field(ge=0.0, le=1.0)
    
    # Big Five
    brand_big_five: Dict[str, float] = Field(default_factory=dict)
    
    # Aaker dimensions
    aaker_dimensions: Dict[str, float] = Field(default_factory=dict)
    
    # Consumer compatibility
    user_compatibility: float = Field(ge=0.0, le=1.0, default=0.5)
    attraction_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_match: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism preferences
    preferred_mechanisms: List[str] = Field(default_factory=list)
    mechanism_alignment: Dict[str, float] = Field(default_factory=dict)
    forbidden_mechanisms: List[str] = Field(default_factory=list)
    
    # Voice characteristics
    voice_style: str = ""
    voice_formality: float = Field(ge=0.0, le=1.0, default=0.5)
    voice_energy: float = Field(ge=0.0, le=1.0, default=0.5)
    voice_humor: float = Field(ge=0.0, le=1.0, default=0.3)
    voice_directness: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Relationship
    relationship_role: str = ""
    social_signal: str = ""
    
    # Demographic impression
    description_as_person: str = ""
    age_impression: str = ""


class BrandPersonalityResult(BaseModel):
    """Result of brand personality atom."""
    
    user_id: str
    request_id: str
    brand_id: Optional[str] = None
    
    # Primary output: compatibility
    brand_compatibility: float = Field(ge=0.0, le=1.0, default=0.5)
    compatibility_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evidence
    brand_evidence: Optional[BrandPersonalityEvidence] = None
    
    # Recommendations
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)
    voice_recommendations: Dict[str, Any] = Field(default_factory=dict)
    
    # Reasoning
    reasoning: str = ""


# =============================================================================
# BRAND PERSONALITY ATOM
# =============================================================================

class BrandPersonalityAtom(BaseAtom):
    """
    Level 2 atom that provides brand personality context.
    
    Dependencies:
    - UserStateAtom (for user archetype if available)
    - PersonalityExpressionAtom (for user Big Five)
    
    Provides to downstream:
    - brand_compatibility (for AdSelectionAtom)
    - preferred_mechanisms (for MechanismActivationAtom)
    - voice_characteristics (for MessageFramingAtom / CopyGeneration)
    
    Intelligence Sources:
    - GRAPH_EMERGENCE (primary - brand profile from Neo4j)
    - BANDIT_POSTERIORS (learned brand-archetype effectiveness)
    """
    
    ATOM_TYPE = AtomType.BRAND_PERSONALITY
    ATOM_NAME = "brand_personality"
    TARGET_CONSTRUCT = "brand_personality"
    
    REQUIRED_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]
    
    OPTIONAL_SOURCES = [
        IntelligenceSourceType.BANDIT_POSTERIORS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._brand_graph_builder = None
    
    async def _get_brand_graph_builder(self):
        """Lazy initialization of brand graph builder."""
        if self._brand_graph_builder is None:
            try:
                from adam.intelligence.knowledge_graph.brand_graph_builder import (
                    get_brand_graph_builder,
                )
                # Get Neo4j driver from bridge
                driver = self.bridge.neo4j_driver if hasattr(self.bridge, 'neo4j_driver') else None
                if driver:
                    self._brand_graph_builder = await get_brand_graph_builder(driver)
            except Exception as e:
                logger.warning(f"Could not initialize brand graph builder: {e}")
        return self._brand_graph_builder
    
    async def _gather_evidence(
        self,
        atom_input: AtomInput,
    ) -> MultiSourceEvidence:
        """
        Gather brand personality evidence.
        
        Primary source: Neo4j graph (brand profile)
        Includes: brand-user compatibility computation
        """
        evidence = MultiSourceEvidence(
            construct=self.TARGET_CONSTRUCT,
        )
        
        # Get brand_id from request context
        brand_id = None
        if atom_input.request_context:
            brand_id = getattr(atom_input.request_context, "brand_id", None)
            # Also check ad candidates for brand
            for candidate in getattr(atom_input.request_context, "ad_candidates", []) or []:
                if isinstance(candidate, dict) and candidate.get("brand_id"):
                    brand_id = candidate["brand_id"]
                    break
        
        if not brand_id:
            logger.debug("No brand_id in request context")
            return evidence
        
        # Get user archetype from upstream atoms
        user_archetype = self._get_user_archetype(atom_input)
        user_big_five = self._get_user_big_five(atom_input)
        
        # Query brand profile and compatibility from Neo4j
        graph_builder = await self._get_brand_graph_builder()
        if graph_builder:
            try:
                compatibility_data = await graph_builder.get_brand_user_compatibility(
                    brand_id=brand_id,
                    user_archetype=user_archetype or "ACHIEVER",
                    user_big_five=user_big_five,
                )
                
                # Build evidence
                brand_evidence = BrandPersonalityEvidence(
                    brand_id=brand_id,
                    brand_name=compatibility_data.get("brand_name", ""),
                    brand_archetype=compatibility_data.get("brand_archetype", "EVERYMAN"),
                    brand_archetype_confidence=0.7,
                    user_compatibility=compatibility_data.get("compatibility", 0.5),
                    attraction_strength=compatibility_data.get("attraction_strength", 0.5),
                    personality_match=compatibility_data.get("personality_match", 0.5),
                    relationship_role=compatibility_data.get("relationship_role", ""),
                    social_signal=compatibility_data.get("social_signal", ""),
                )
                
                # Also get full profile for mechanisms
                profile_data = await graph_builder.get_brand_profile(brand_id)
                if profile_data:
                    # Extract mechanism preferences
                    mechanisms = profile_data.get("mechanisms", [])
                    for mech in mechanisms:
                        if mech.get("preferred"):
                            brand_evidence.preferred_mechanisms.append(mech["name"])
                        brand_evidence.mechanism_alignment[mech["name"]] = mech.get("alignment", 0.5)
                    
                    # Extract voice
                    brand_evidence.voice_style = profile_data.get("voice_style", "")
                    brand_evidence.voice_formality = profile_data.get("voice_formality", 0.5)
                    brand_evidence.voice_energy = profile_data.get("voice_energy", 0.5)
                    brand_evidence.voice_humor = profile_data.get("voice_humor", 0.3)
                    brand_evidence.voice_directness = profile_data.get("voice_directness", 0.5)
                    brand_evidence.description_as_person = profile_data.get("description_as_person", "")
                
                # Add to evidence
                evidence.evidence[IntelligenceSourceType.GRAPH_EMERGENCE] = IntelligenceEvidence(
                    source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                    construct=self.TARGET_CONSTRUCT,
                    value=compatibility_data.get("compatibility", 0.5),
                    confidence=0.8 if compatibility_data.get("found") else 0.3,
                    metadata={
                        "brand_evidence": brand_evidence.model_dump(),
                        "found": compatibility_data.get("found", False),
                    },
                    timestamp=datetime.now(timezone.utc),
                    strength=EvidenceStrength.MODERATE if compatibility_data.get("found") else EvidenceStrength.WEAK,
                )
                
            except Exception as e:
                logger.warning(f"Error getting brand compatibility: {e}")
        
        return evidence
    
    def _get_user_archetype(self, atom_input: AtomInput) -> Optional[str]:
        """Extract user archetype from upstream atoms."""
        # Check PersonalityExpressionAtom output
        personality_output = atom_input.get_upstream("atom_personality_expression")
        if personality_output and personality_output.secondary_assessments:
            archetype = personality_output.secondary_assessments.get("archetype")
            if archetype:
                return archetype
        
        # Check UserStateAtom output
        user_state = atom_input.get_upstream("atom_user_state")
        if user_state and user_state.secondary_assessments:
            archetype = user_state.secondary_assessments.get("archetype")
            if archetype:
                return archetype
        
        # Check request context
        if atom_input.request_context:
            return getattr(atom_input.request_context, "user_archetype", None)
        
        return None
    
    def _get_user_big_five(self, atom_input: AtomInput) -> Optional[Dict[str, float]]:
        """Extract user Big Five from upstream atoms."""
        personality_output = atom_input.get_upstream("atom_personality_expression")
        if personality_output and personality_output.inferred_states:
            return {
                "openness": personality_output.inferred_states.get("openness", 0.5),
                "conscientiousness": personality_output.inferred_states.get("conscientiousness", 0.5),
                "extraversion": personality_output.inferred_states.get("extraversion", 0.5),
                "agreeableness": personality_output.inferred_states.get("agreeableness", 0.5),
                "neuroticism": personality_output.inferred_states.get("neuroticism", 0.5),
            }
        
        # Check request context
        if atom_input.request_context:
            return getattr(atom_input.request_context, "user_big_five", None)
        
        return None
    
    async def _fuse_without_claude(
        self,
        evidence: MultiSourceEvidence,
        atom_input: AtomInput,
    ) -> FusionResult:
        """
        Fuse brand evidence without Claude.
        
        Primary logic:
        1. Use graph compatibility as base
        2. Adjust based on mechanism alignment
        3. Generate recommendations
        """
        # Get brand evidence
        graph_evidence = evidence.evidence.get(IntelligenceSourceType.GRAPH_EMERGENCE)
        
        if not graph_evidence or not graph_evidence.metadata.get("found"):
            return FusionResult(
                construct=self.TARGET_CONSTRUCT,
                assessment="0.5",
                assessment_value=0.5,
                confidence=0.3,
                reasoning="No brand profile found in graph",
                contributing_sources=[],
            )
        
        brand_data = graph_evidence.metadata.get("brand_evidence", {})
        
        # Primary assessment: user compatibility
        compatibility = brand_data.get("user_compatibility", 0.5)
        
        # Adjust based on archetype attraction
        attraction = brand_data.get("attraction_strength", 0.5)
        personality_match = brand_data.get("personality_match", 0.5)
        
        # Weighted combination
        assessment = (
            compatibility * 0.5 +
            attraction * 0.3 +
            personality_match * 0.2
        )
        
        return FusionResult(
            construct=self.TARGET_CONSTRUCT,
            assessment=str(assessment),
            assessment_value=assessment,
            confidence=graph_evidence.confidence,
            reasoning=f"Brand-user compatibility: {compatibility:.2f}, "
                      f"attraction: {attraction:.2f}, personality match: {personality_match:.2f}",
            contributing_sources=[IntelligenceSourceType.GRAPH_EMERGENCE],
            source_weights={
                IntelligenceSourceType.GRAPH_EMERGENCE: 1.0,
            },
        )
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build brand personality output."""
        
        # Extract brand evidence
        brand_evidence = None
        graph_evi = evidence.evidence.get(IntelligenceSourceType.GRAPH_EMERGENCE)
        if graph_evi and graph_evi.metadata.get("brand_evidence"):
            brand_evidence = BrandPersonalityEvidence(**graph_evi.metadata["brand_evidence"])
        
        # Build recommendations
        recommended_mechanisms = []
        mechanism_weights = {}
        voice_recommendations = {}
        
        if brand_evidence:
            recommended_mechanisms = brand_evidence.preferred_mechanisms
            mechanism_weights = brand_evidence.mechanism_alignment
            voice_recommendations = {
                "style": brand_evidence.voice_style,
                "formality": brand_evidence.voice_formality,
                "energy": brand_evidence.voice_energy,
                "humor": brand_evidence.voice_humor,
                "directness": brand_evidence.voice_directness,
            }

        # DSP alignment edge enrichment: enrich brand-mechanism compatibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp and mechanism_weights:
            # Alignment edges: brand personality → mechanism alignment from DSP graph
            alignment_edges = dsp.get_alignment_edges()
            if alignment_edges:
                for edge in alignment_edges:
                    target = edge.get("target_id", "")
                    strength = edge.get("strength", 0.0)
                    # If the alignment edge target matches a mechanism, boost it
                    if target in mechanism_weights:
                        mechanism_weights[target] = min(1.0, mechanism_weights[target] + strength * 0.10)
                    # Also check if target is a personality trait that maps to mechanisms
                    # (alignment edges can point to personality constructs)

            # Empirical effectiveness: weight mechanism preferences by data
            empirical = dsp.get_all_empirical()
            for mech in list(mechanism_weights.keys()):
                emp = empirical.get(mech)
                if emp and emp.get("sample_size", 0) > 50:
                    success = emp.get("success_rate", 0.5)
                    mechanism_weights[mech] = min(1.0, mechanism_weights[mech] + (success - 0.5) * 0.1)

            # Update recommended_mechanisms based on new weights
            if mechanism_weights:
                recommended_mechanisms = sorted(
                    mechanism_weights.keys(),
                    key=lambda m: mechanism_weights[m],
                    reverse=True
                )[:5]

        # Build result
        result = BrandPersonalityResult(
            user_id=atom_input.user_id,
            request_id=atom_input.request_id,
            brand_id=brand_evidence.brand_id if brand_evidence else None,
            brand_compatibility=fusion_result.assessment,
            compatibility_confidence=fusion_result.confidence,
            brand_evidence=brand_evidence,
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_weights,
            voice_recommendations=voice_recommendations,
            reasoning=fusion_result.reasoning,
        )
        
        # Build atom output
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=str(fusion_result.assessment),
            overall_confidence=fusion_result.confidence,
            evidence_package=evidence,
            inferred_states={
                "brand_compatibility": fusion_result.assessment,
                "attraction_strength": brand_evidence.attraction_strength if brand_evidence else 0.5,
                "personality_match": brand_evidence.personality_match if brand_evidence else 0.5,
            },
            secondary_assessments={
                "brand_archetype": brand_evidence.brand_archetype if brand_evidence else None,
                "brand_id": brand_evidence.brand_id if brand_evidence else None,
                "preferred_mechanisms": recommended_mechanisms,
                "voice_style": brand_evidence.voice_style if brand_evidence else None,
                "relationship_role": brand_evidence.relationship_role if brand_evidence else None,
            },
            recommendations={
                "mechanisms": recommended_mechanisms,
                "mechanism_weights": mechanism_weights,
                "voice": voice_recommendations,
            },
        )
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query construct-specific sources for brand personality.
        
        Brand personality gets evidence from:
        - GRAPH_EMERGENCE: Brand profile from Neo4j
        - BANDIT_POSTERIORS: Learned brand-archetype effectiveness
        """
        if source == IntelligenceSourceType.GRAPH_EMERGENCE:
            # Brand profile is gathered in _gather_evidence
            # This is called if we need to re-query
            return await self._query_brand_profile(atom_input)
        
        if source == IntelligenceSourceType.BANDIT_POSTERIORS:
            # Query learned brand effectiveness
            return await self._query_brand_effectiveness(atom_input)
        
        return None
    
    async def _query_brand_profile(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query brand profile from Neo4j."""
        brand_id = None
        if atom_input.request_context:
            brand_id = getattr(atom_input.request_context, "brand_id", None)
        
        if not brand_id:
            return None
        
        graph_builder = await self._get_brand_graph_builder()
        if not graph_builder:
            return None
        
        try:
            profile_data = await graph_builder.get_brand_profile(brand_id)
            if profile_data:
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                    construct=self.TARGET_CONSTRUCT,
                    value=0.7,
                    confidence=0.8,
                    metadata={"brand_profile": profile_data},
                    timestamp=datetime.now(timezone.utc),
                    strength=EvidenceStrength.MODERATE,
                )
        except Exception as e:
            logger.warning(f"Error querying brand profile: {e}")
        
        return None
    
    async def _query_brand_effectiveness(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query learned brand-archetype effectiveness from bandits."""
        # This would query Thompson Sampling posteriors for brand effectiveness
        # For now, return None as this requires bandit integration
        return None


# =============================================================================
# FACTORY
# =============================================================================

def create_brand_personality_atom(
    bridge: "InteractionBridge",
    blackboard: Optional["BlackboardService"] = None,
) -> BrandPersonalityAtom:
    """Create a brand personality atom."""
    from adam.atoms.models.atom_io import AtomConfig, AtomTier
    
    config = AtomConfig(
        atom_id="atom_brand_personality",
        atom_type=AtomType.CUSTOM,
        tier=AtomTier.STANDARD,
        use_claude_fusion=False,  # Don't need Claude for brand matching
        required_sources=[IntelligenceSourceType.GRAPH_EMERGENCE],
        optional_sources=[IntelligenceSourceType.BANDIT_POSTERIORS],
    )
    
    return BrandPersonalityAtom(
        config=config,
        bridge=bridge,
        blackboard=blackboard,
    )
