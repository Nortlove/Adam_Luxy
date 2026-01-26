# =============================================================================
# ADAM Review Intelligence Atom
# Location: adam/atoms/core/review_intelligence.py
# =============================================================================

"""
REVIEW INTELLIGENCE ATOM

Provides customer intelligence from product review analysis as evidence
for the AtomDAG. This is a foundational atom that informs all other atoms
with real customer psychology derived from reviews.

Integration points:
- Feeds into UserStateAtom (real personality profiles)
- Feeds into RegulatoryFocusAtom (promotion/prevention from reviews)
- Feeds into PersonalityExpressionAtom (Big Five from reviewers)
- Feeds into MechanismActivationAtom (predicted mechanism effectiveness)
- Feeds into MessageFramingAtom (customer language patterns)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    EvidenceStrength,
    FusionResult,
)
from adam.atoms.models.atom_io import (
    AtomInput,
    AtomOutput,
    AtomConfig,
    AtomTier,
)
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.blackboard.models.core import BlackboardZone
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)

logger = logging.getLogger(__name__)


class ReviewIntelligenceAtom(BaseAtom):
    """
    Atom that provides customer intelligence from product review analysis.
    
    This atom:
    1. Retrieves CustomerIntelligenceProfile from Blackboard Zone 6
    2. Queries Neo4j for related buyer archetypes
    3. Emits evidence about real customer psychology
    4. Provides language patterns for copy generation
    
    The intelligence from this atom flows into all other atoms, making
    review analysis a foundational source of psychological insight.
    """
    
    ATOM_TYPE = AtomType.CUSTOM
    ATOM_NAME = "review_intelligence"
    TARGET_CONSTRUCT = "customer_psychology"
    
    # Review intelligence sources
    REQUIRED_SOURCES: List[IntelligenceSourceType] = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,  # Review data
    ]
    
    OPTIONAL_SOURCES: List[IntelligenceSourceType] = [
        IntelligenceSourceType.GRAPH_EMERGENCE,     # Buyer archetype relationships
        IntelligenceSourceType.COHORT_ORGANIZATION, # Similar customer cohorts
    ]
    
    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query review intelligence specific sources."""
        
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_review_intelligence(atom_input)
        
        if source == IntelligenceSourceType.GRAPH_EMERGENCE:
            return await self._query_buyer_archetypes(atom_input)
        
        if source == IntelligenceSourceType.COHORT_ORGANIZATION:
            return await self._query_similar_customers(atom_input)
        
        return None
    
    async def _query_review_intelligence(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query customer intelligence from Blackboard Zone 6.
        
        Zone 6 contains the CustomerIntelligenceProfile populated by the
        ReviewIntelligenceOrchestrator during request processing.
        """
        try:
            # Try to read from Zone 6
            zone6_data = await self.blackboard.read_zone(
                atom_input.request_id,
                BlackboardZone.ZONE_6_REVIEW_INTELLIGENCE,
            )
            
            if zone6_data and "customer_intelligence" in zone6_data:
                ci = zone6_data["customer_intelligence"]
                
                # Extract key insights
                dominant_archetype = ci.get("dominant_archetype", "Unknown")
                archetype_confidence = ci.get("archetype_confidence", 0.5)
                reviews_analyzed = ci.get("reviews_analyzed", 0)
                
                # Build evidence
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=dominant_archetype,
                    assessment_value=archetype_confidence,
                    confidence=min(0.9, 0.5 + (reviews_analyzed / 200)),  # More reviews = more confidence
                    confidence_semantics=ConfidenceSemantics.FREQUENTIST,
                    strength=self._reviews_to_strength(reviews_analyzed),
                    support_count=reviews_analyzed,
                    reasoning=f"Dominant buyer archetype '{dominant_archetype}' from {reviews_analyzed} reviews",
                    metadata={
                        "buyer_archetypes": ci.get("buyer_archetypes", {}),
                        "personality_traits": {
                            "openness": ci.get("avg_openness", 0.5),
                            "conscientiousness": ci.get("avg_conscientiousness", 0.5),
                            "extraversion": ci.get("avg_extraversion", 0.5),
                            "agreeableness": ci.get("avg_agreeableness", 0.5),
                            "neuroticism": ci.get("avg_neuroticism", 0.5),
                        },
                        "regulatory_focus": ci.get("regulatory_focus", {}),
                        "purchase_motivations": ci.get("purchase_motivations", []),
                        "mechanism_predictions": ci.get("mechanism_predictions", {}),
                        "language_intelligence": ci.get("language_intelligence", {}),
                    },
                )
        
        except Exception as e:
            logger.debug(f"Review intelligence query failed: {e}")
        
        # Try to get from atom_input context (may be passed directly)
        if atom_input.context and "customer_intelligence" in atom_input.context:
            ci = atom_input.context["customer_intelligence"]
            return self._profile_to_evidence(ci)
        
        return None
    
    async def _query_buyer_archetypes(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query buyer archetype relationships from Neo4j.
        
        Uses RESPONDS_TO_MECHANISM edges to get mechanism effectiveness
        for detected buyer archetypes.
        """
        try:
            # Get dominant archetype from context or Zone 6
            dominant_archetype = None
            
            if atom_input.context and "dominant_archetype" in atom_input.context:
                dominant_archetype = atom_input.context["dominant_archetype"]
            
            if not dominant_archetype:
                # Try Zone 6
                zone6_data = await self.blackboard.read_zone(
                    atom_input.request_id,
                    BlackboardZone.ZONE_6_REVIEW_INTELLIGENCE,
                )
                if zone6_data and "customer_intelligence" in zone6_data:
                    dominant_archetype = zone6_data["customer_intelligence"].get("dominant_archetype")
            
            if not dominant_archetype or dominant_archetype == "Unknown":
                return None
            
            # Query Neo4j for archetype mechanism effectiveness
            from adam.intelligence.graph_edge_service import get_graph_edge_service
            
            edge_service = get_graph_edge_service()
            priors = await edge_service.get_archetype_mechanism_priors(dominant_archetype)
            
            if priors:
                # Find best mechanism
                best_prior = max(priors, key=lambda p: p.success_rate)
                
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.GRAPH_EMERGENCE,
                    construct="mechanism_effectiveness",
                    assessment=best_prior.mechanism_name,
                    assessment_value=best_prior.success_rate,
                    confidence=best_prior.confidence,
                    confidence_semantics=ConfidenceSemantics.POSTERIOR_DISTRIBUTION,
                    strength=self._sample_to_strength(best_prior.sample_size),
                    support_count=best_prior.sample_size,
                    reasoning=f"Archetype '{dominant_archetype}' responds best to '{best_prior.mechanism_name}'",
                    metadata={
                        "archetype": dominant_archetype,
                        "all_mechanisms": {
                            p.mechanism_name: {
                                "success_rate": p.success_rate,
                                "confidence": p.confidence,
                            }
                            for p in priors
                        },
                    },
                )
        
        except Exception as e:
            logger.debug(f"Buyer archetype query failed: {e}")
        
        return None
    
    async def _query_similar_customers(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """
        Query cohort of similar customers based on review psychology.
        """
        # This would query Neo4j for users with similar CustomerIntelligence
        # profiles to leverage cohort-level learning
        return None  # TODO: Implement cohort matching
    
    def _profile_to_evidence(
        self,
        profile: Dict[str, Any],
    ) -> IntelligenceEvidence:
        """Convert CustomerIntelligenceProfile dict to evidence."""
        dominant_archetype = profile.get("dominant_archetype", "Unknown")
        archetype_confidence = profile.get("archetype_confidence", 0.5)
        reviews_analyzed = profile.get("reviews_analyzed", 0)
        
        return IntelligenceEvidence(
            source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
            construct=self.TARGET_CONSTRUCT,
            assessment=dominant_archetype,
            assessment_value=archetype_confidence,
            confidence=min(0.9, 0.5 + (reviews_analyzed / 200)),
            confidence_semantics=ConfidenceSemantics.FREQUENTIST,
            strength=self._reviews_to_strength(reviews_analyzed),
            support_count=reviews_analyzed,
            reasoning=f"Dominant buyer archetype '{dominant_archetype}' from {reviews_analyzed} reviews",
            metadata={
                "buyer_archetypes": profile.get("buyer_archetypes", {}),
                "mechanism_predictions": profile.get("mechanism_predictions", {}),
                "language_intelligence": profile.get("language_intelligence", {}),
            },
        )
    
    def _reviews_to_strength(self, count: int) -> EvidenceStrength:
        """Convert review count to evidence strength."""
        if count < 10:
            return EvidenceStrength.WEAK
        elif count < 50:
            return EvidenceStrength.MODERATE
        elif count < 100:
            return EvidenceStrength.STRONG
        else:
            return EvidenceStrength.VERY_STRONG
    
    def _sample_to_strength(self, count: int) -> EvidenceStrength:
        """Convert sample size to evidence strength."""
        if count < 20:
            return EvidenceStrength.WEAK
        elif count < 100:
            return EvidenceStrength.MODERATE
        elif count < 500:
            return EvidenceStrength.STRONG
        else:
            return EvidenceStrength.VERY_STRONG
    
    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build the review intelligence output."""
        # Extract key insights from evidence
        buyer_archetypes: Dict[str, float] = {}
        personality_traits: Dict[str, float] = {}
        regulatory_focus: Dict[str, float] = {}
        mechanism_predictions: Dict[str, float] = {}
        language_intelligence: Dict[str, Any] = {}
        
        for source_type, evi in evidence.evidence.items():
            if evi.metadata:
                if "buyer_archetypes" in evi.metadata:
                    buyer_archetypes.update(evi.metadata["buyer_archetypes"])
                if "personality_traits" in evi.metadata:
                    personality_traits.update(evi.metadata["personality_traits"])
                if "regulatory_focus" in evi.metadata:
                    regulatory_focus.update(evi.metadata["regulatory_focus"])
                if "mechanism_predictions" in evi.metadata:
                    mechanism_predictions.update(evi.metadata["mechanism_predictions"])
                if "language_intelligence" in evi.metadata:
                    language_intelligence.update(evi.metadata["language_intelligence"])
        
        # Build recommended mechanisms from predictions
        recommended_mechanisms = sorted(
            mechanism_predictions.keys(),
            key=lambda m: mechanism_predictions[m],
            reverse=True,
        )[:3]
        
        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            primary_assessment=fusion_result.assessment,
            overall_confidence=fusion_result.confidence,
            recommended_mechanisms=recommended_mechanisms,
            mechanism_weights=mechanism_predictions,
            metadata={
                "buyer_archetypes": buyer_archetypes,
                "dominant_archetype": fusion_result.assessment,
                "archetype_confidence": fusion_result.confidence,
                "personality_traits": personality_traits,
                "regulatory_focus": regulatory_focus,
                "language_intelligence": language_intelligence,
                "sources_used": [s.value for s in fusion_result.sources_used] if fusion_result.sources_used else [],
            },
        )


# =============================================================================
# SINGLETON
# =============================================================================

_atom: Optional[ReviewIntelligenceAtom] = None


def get_review_intelligence_atom(
    blackboard=None,
    bridge=None,
) -> ReviewIntelligenceAtom:
    """Get singleton Review Intelligence Atom."""
    global _atom
    if _atom is None:
        # Lazy imports to avoid circular dependencies
        from adam.blackboard.service import get_blackboard_service
        from adam.graph_reasoning.bridge import get_interaction_bridge
        
        _atom = ReviewIntelligenceAtom(
            blackboard=blackboard or get_blackboard_service(),
            bridge=bridge or get_interaction_bridge(),
        )
    return _atom
