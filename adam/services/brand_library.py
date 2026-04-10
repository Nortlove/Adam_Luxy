# =============================================================================
# ADAM Brand Library Service
# Location: adam/services/brand_library.py
# =============================================================================

"""
BRAND LIBRARY SERVICE

Provides brand intelligence for the decision workflow.

This service manages:
1. Brand constraints (what messaging is allowed)
2. Brand voice (tone, style, personality)
3. Brand positioning (psychological positioning from brand copy)

The service integrates with:
- Neo4j for stored brand profiles
- Brand Trait Extraction for dynamic analysis
- Learned priors from Amazon brand copy analysis
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

@dataclass
class BrandVoice:
    """Brand voice characteristics."""
    
    tone: str = "neutral"  # friendly, professional, casual, authoritative
    formality: float = 0.5  # 0 = very casual, 1 = very formal
    energy: float = 0.5  # 0 = calm, 1 = energetic
    humor: float = 0.3  # 0 = serious, 1 = humorous
    directness: float = 0.5  # 0 = indirect, 1 = direct
    
    # Persuasion style from brand copy analysis
    primary_persuasion_style: str = "balanced"  # emotional, rational, social_proof, authority
    secondary_persuasion_style: Optional[str] = None


@dataclass
class BrandProfile:
    """Complete brand profile."""
    
    brand_id: str
    name: str
    
    # Constraints
    constraints: List[str] = field(default_factory=list)
    prohibited_topics: List[str] = field(default_factory=list)
    required_disclosures: List[str] = field(default_factory=list)
    
    # Voice
    voice: BrandVoice = field(default_factory=BrandVoice)
    
    # Psychological positioning (from brand copy analysis)
    brand_archetype: Optional[str] = None  # Hero, Caregiver, Rebel, etc.
    positioning_traits: Dict[str, float] = field(default_factory=dict)
    
    # Target alignment
    target_customer_archetypes: List[str] = field(default_factory=list)
    mechanism_preferences: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# SERVICE
# =============================================================================

class BrandLibraryService:
    """
    Service for accessing brand intelligence.
    
    Provides brand profiles including:
    - Brand constraints (messaging rules)
    - Brand voice (tone, style)
    - Brand positioning (psychological profile from brand copy)
    
    The service can:
    1. Query Neo4j for stored brand profiles
    2. Analyze brand copy dynamically via BrandTraitAnalyzer
    3. Use learned priors from Amazon brand copy analysis
    """
    
    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
    ):
        self.driver = neo4j_driver
        
        # Cache for brand profiles
        self._cache: Dict[str, BrandProfile] = {}
        
        logger.info("BrandLibraryService initialized")
    
    async def get_brand(self, brand_id: str) -> Optional[BrandProfile]:
        """
        Get brand profile by ID.
        
        Attempts to:
        1. Check local cache
        2. Query Neo4j for stored profile
        3. Return default profile if not found
        """
        
        # Check cache
        if brand_id in self._cache:
            return self._cache[brand_id]
        
        # Try Neo4j
        if self.driver:
            profile = await self._query_brand_from_graph(brand_id)
            if profile:
                self._cache[brand_id] = profile
                return profile
        
        # Return default profile for unknown brands
        default_profile = BrandProfile(
            brand_id=brand_id,
            name=brand_id,
            constraints=[],
            voice=BrandVoice(),
        )
        
        logger.debug(f"Using default profile for brand: {brand_id}")
        return default_profile
    
    async def _query_brand_from_graph(self, brand_id: str) -> Optional[BrandProfile]:
        """Query brand profile from Neo4j."""
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (b:Brand {brand_id: $brand_id})
                    OPTIONAL MATCH (b)-[:HAS_CONSTRAINT]->(c:Constraint)
                    OPTIONAL MATCH (b)-[:HAS_ARCHETYPE]->(a:Archetype)
                    RETURN b, 
                           COLLECT(DISTINCT c.text) as constraints,
                           a.name as archetype
                    """,
                    brand_id=brand_id
                )
                
                record = await result.single()
                if not record:
                    return None
                
                brand_data = record["b"]
                
                profile = BrandProfile(
                    brand_id=brand_id,
                    name=brand_data.get("name", brand_id),
                    constraints=record["constraints"] or [],
                    brand_archetype=record["archetype"],
                    voice=BrandVoice(
                        tone=brand_data.get("voice_tone", "neutral"),
                        formality=brand_data.get("voice_formality", 0.5),
                        energy=brand_data.get("voice_energy", 0.5),
                    ),
                )
                
                return profile
                
        except Exception as e:
            logger.error(f"Error querying brand from graph: {e}")
            return None
    
    async def analyze_brand_copy(
        self,
        brand_id: str,
        brand_copy: str,
    ) -> Dict[str, Any]:
        """
        Analyze brand copy for psychological positioning.
        
        Uses BrandTraitAnalyzer to extract:
        - Trust communication style
        - Authority positioning
        - Emotional vs rational appeal
        - Innovation vs heritage positioning
        """
        
        try:
            from adam.intelligence.brand_trait_extraction import (
                BrandTraitAnalyzer,
                get_brand_trait_analyzer,
            )
            
            analyzer = get_brand_trait_analyzer()
            result = analyzer.analyze(brand_copy)
            
            # Update cached profile with analysis results
            if brand_id in self._cache:
                self._cache[brand_id].positioning_traits = {
                    trait.trait_id: trait.score
                    for trait in result.trait_scores
                }
            
            return {
                "brand_id": brand_id,
                "traits": {t.trait_id: t.score for t in result.trait_scores},
                "primary_trait": max(result.trait_scores, key=lambda t: t.score).trait_id if result.trait_scores else None,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing brand copy: {e}")
            return {"brand_id": brand_id, "traits": {}, "error": str(e)}
    
    async def get_brand_mechanism_alignment(
        self,
        brand_id: str,
        mechanisms: List[str],
    ) -> Dict[str, float]:
        """
        Get alignment scores between brand and mechanisms.
        
        Returns how well each mechanism fits the brand's positioning.
        """
        
        profile = await self.get_brand(brand_id)
        if not profile or not profile.mechanism_preferences:
            # Default: all mechanisms equally weighted
            return {m: 0.5 for m in mechanisms}
        
        return {
            m: profile.mechanism_preferences.get(m, 0.5)
            for m in mechanisms
        }


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[BrandLibraryService] = None


def get_brand_library_service(
    neo4j_driver: Optional[AsyncDriver] = None,
) -> BrandLibraryService:
    """Get or create the brand library service singleton."""
    global _service
    
    if _service is None:
        _service = BrandLibraryService(neo4j_driver=neo4j_driver)
    
    return _service
