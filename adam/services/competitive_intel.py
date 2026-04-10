# =============================================================================
# ADAM Competitive Intelligence Service
# Location: adam/services/competitive_intel.py
# =============================================================================

"""
COMPETITIVE INTELLIGENCE SERVICE

Provides competitive landscape analysis for the decision workflow.

This service analyzes:
1. Competing brands in a category
2. Share of voice and positioning
3. Mechanism saturation (what persuasion techniques are overused)
4. Differentiation opportunities

Key Insight for Psycholinguistic Advertising:
- If competitors heavily use "social proof", that mechanism becomes saturated
- Finding underutilized mechanisms creates differentiation
- Understanding competitor positioning helps find psychological white space
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
class CompetitorProfile:
    """Profile of a competing brand."""
    
    brand_id: str
    name: str
    market_share: float = 0.0
    
    # Psychological positioning
    primary_mechanisms: List[str] = field(default_factory=list)
    primary_archetypes: List[str] = field(default_factory=list)
    
    # Message characteristics
    tone: str = "neutral"
    price_positioning: str = "mid"  # budget, mid, premium, luxury


@dataclass
class CompetitiveLandscape:
    """Complete competitive landscape for a category."""
    
    category_id: str
    
    # Competitors
    competitors: List[CompetitorProfile] = field(default_factory=list)
    
    # Mechanism analysis
    mechanism_saturation: Dict[str, float] = field(default_factory=dict)  # 0 = unused, 1 = heavily used
    mechanism_opportunities: List[str] = field(default_factory=list)  # Underused mechanisms
    
    # Archetype analysis
    archetype_concentration: Dict[str, float] = field(default_factory=dict)
    archetype_white_space: List[str] = field(default_factory=list)
    
    # Market dynamics
    total_competitors: int = 0
    market_maturity: str = "mature"  # emerging, growing, mature, declining
    
    # Recommendations
    differentiation_opportunities: List[str] = field(default_factory=list)


# =============================================================================
# MECHANISM SATURATION DEFAULTS
# =============================================================================

# Default saturation levels based on general market research
# These represent typical overuse patterns in advertising
DEFAULT_MECHANISM_SATURATION = {
    "social_proof": 0.85,  # Heavily overused ("Join millions...")
    "scarcity": 0.75,  # Often used ("Limited time!")
    "authority": 0.65,  # Common ("Experts recommend...")
    "reciprocity": 0.45,  # Moderate use
    "commitment": 0.40,  # Moderate use
    "liking": 0.55,  # Common (celebrity endorsements)
    "storytelling": 0.50,  # Moderate
    "fear_appeal": 0.60,  # Common in some categories
    "humor": 0.35,  # Less common in direct response
    "nostalgia": 0.30,  # Underutilized
    "curiosity_gap": 0.45,  # Moderate
    "cognitive_ease": 0.55,  # Often implicit
    "emotional_contagion": 0.40,  # Moderate
    "identity_appeal": 0.50,  # Growing
    "loss_aversion": 0.70,  # Common
}


# =============================================================================
# SERVICE
# =============================================================================

class CompetitiveIntelService:
    """
    Service for competitive intelligence.
    
    Provides:
    - Category competitive landscape
    - Mechanism saturation analysis
    - Differentiation opportunities
    
    The service helps find "psychological white space" - 
    mechanisms and approaches that are underutilized by competitors.
    """
    
    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
    ):
        self.driver = neo4j_driver
        
        # Cache for landscapes
        self._cache: Dict[str, CompetitiveLandscape] = {}
        
        logger.info("CompetitiveIntelService initialized")
    
    async def get_landscape(
        self,
        category_id: Optional[str] = None,
    ) -> CompetitiveLandscape:
        """
        Get competitive landscape for a category.
        
        If no category specified, returns general market landscape.
        """
        
        cache_key = category_id or "general"
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try to build from graph
        if self.driver and category_id:
            landscape = await self._query_landscape_from_graph(category_id)
            if landscape:
                self._cache[cache_key] = landscape
                return landscape
        
        # Return intelligent defaults
        landscape = self._build_default_landscape(category_id)
        self._cache[cache_key] = landscape
        return landscape
    
    async def _query_landscape_from_graph(
        self,
        category_id: str,
    ) -> Optional[CompetitiveLandscape]:
        """Query competitive landscape from Neo4j."""
        
        try:
            async with self.driver.session() as session:
                # Get competitors in category
                result = await session.run(
                    """
                    MATCH (c:Category {category_id: $category_id})<-[:IN_CATEGORY]-(b:Brand)
                    OPTIONAL MATCH (b)-[:USES_MECHANISM]->(m:Mechanism)
                    RETURN b.brand_id as brand_id,
                           b.name as name,
                           b.market_share as market_share,
                           COLLECT(DISTINCT m.mechanism_id) as mechanisms
                    LIMIT 20
                    """,
                    category_id=category_id
                )
                
                records = await result.data()
                
                if not records:
                    return None
                
                # Build competitor profiles
                competitors = []
                mechanism_counts: Dict[str, int] = {}
                
                for record in records:
                    comp = CompetitorProfile(
                        brand_id=record["brand_id"],
                        name=record["name"] or record["brand_id"],
                        market_share=record["market_share"] or 0.0,
                        primary_mechanisms=record["mechanisms"] or [],
                    )
                    competitors.append(comp)
                    
                    # Count mechanism usage
                    for mech in comp.primary_mechanisms:
                        mechanism_counts[mech] = mechanism_counts.get(mech, 0) + 1
                
                # Calculate saturation
                total_competitors = len(competitors)
                mechanism_saturation = {
                    mech: count / total_competitors
                    for mech, count in mechanism_counts.items()
                }
                
                # Find opportunities (saturation < 0.3)
                opportunities = [
                    mech for mech, sat in DEFAULT_MECHANISM_SATURATION.items()
                    if mechanism_saturation.get(mech, sat) < 0.3
                ]
                
                landscape = CompetitiveLandscape(
                    category_id=category_id,
                    competitors=competitors,
                    mechanism_saturation=mechanism_saturation,
                    mechanism_opportunities=opportunities,
                    total_competitors=total_competitors,
                )
                
                return landscape
                
        except Exception as e:
            logger.error(f"Error querying competitive landscape: {e}")
            return None
    
    def _build_default_landscape(
        self,
        category_id: Optional[str],
    ) -> CompetitiveLandscape:
        """Build intelligent default landscape."""
        
        # Start with default saturation
        saturation = DEFAULT_MECHANISM_SATURATION.copy()
        
        # Find underutilized mechanisms (saturation < 0.4)
        opportunities = [
            mech for mech, sat in saturation.items()
            if sat < 0.4
        ]
        
        # Derive differentiation recommendations
        differentiation = []
        if saturation.get("nostalgia", 0) < 0.4:
            differentiation.append("Consider nostalgia-based messaging - underutilized in market")
        if saturation.get("humor", 0) < 0.4:
            differentiation.append("Humor could create differentiation in a serious market")
        if saturation.get("emotional_contagion", 0) < 0.5:
            differentiation.append("Emotional storytelling could stand out")
        
        return CompetitiveLandscape(
            category_id=category_id or "general",
            mechanism_saturation=saturation,
            mechanism_opportunities=opportunities,
            differentiation_opportunities=differentiation,
            total_competitors=0,  # Unknown
            market_maturity="mature",
        )
    
    async def get_mechanism_opportunity_score(
        self,
        category_id: Optional[str],
        mechanism_id: str,
    ) -> float:
        """
        Get opportunity score for using a specific mechanism.
        
        Higher score = less saturated = more differentiation potential.
        """
        
        landscape = await self.get_landscape(category_id)
        saturation = landscape.mechanism_saturation.get(
            mechanism_id, 
            DEFAULT_MECHANISM_SATURATION.get(mechanism_id, 0.5)
        )
        
        # Opportunity = 1 - saturation
        return 1.0 - saturation


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[CompetitiveIntelService] = None


def get_competitive_intel_service(
    neo4j_driver: Optional[AsyncDriver] = None,
) -> CompetitiveIntelService:
    """Get or create the competitive intel service singleton."""
    global _service
    
    if _service is None:
        _service = CompetitiveIntelService(neo4j_driver=neo4j_driver)
    
    return _service
