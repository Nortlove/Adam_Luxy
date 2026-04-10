# =============================================================================
# ADAM Archetype Service
# Location: adam/services/archetype_service.py
# =============================================================================

"""
ARCHETYPE SERVICE

Provides archetype-based decision shortcuts for the fast execution path.

Archetypes represent validated patterns learned from:
1. Billion+ Amazon reviews (customer archetypes)
2. Brand copy analysis (brand archetypes)
3. Mechanism-outcome correlations (effectiveness patterns)

Key Psycholinguistic Insight:
- Archetypes compress complex psychological profiles into actionable patterns
- They enable fast path decisions without full reasoning
- They represent validated wisdom from historical data
- They're continuously updated via the learning loop
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

@dataclass
class CustomerArchetype:
    """Validated customer archetype pattern."""
    
    archetype_id: str
    name: str
    description: str
    
    # Psychological profile
    psychological_dimensions: Dict[str, float] = field(default_factory=dict)
    
    # Mechanism effectiveness (learned from outcomes)
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    
    # Message recommendations
    recommended_tone: str = "neutral"
    recommended_complexity: str = "medium"
    recommended_frame: str = "balanced"  # gain, loss, balanced
    
    # Validation metrics
    sample_size: int = 0
    confidence: float = 0.5
    last_updated: Optional[str] = None


@dataclass
class ArchetypeOutputs:
    """Pre-computed outputs for archetype-based fast path."""
    
    archetype_id: str
    
    # Mechanism weights (ready to use for scoring)
    mechanism_weights: Dict[str, float] = field(default_factory=dict)
    
    # Frame recommendation
    message_frame: str = "balanced"
    message_tone: str = "neutral"
    
    # Confidence in this archetype matching
    match_confidence: float = 0.5
    
    # Evidence used
    evidence_count: int = 0


# =============================================================================
# DEFAULT ARCHETYPES (from Amazon review analysis)
# =============================================================================

# These represent validated patterns from deep learning on 1B+ reviews
DEFAULT_ARCHETYPES = {
    "value_conscious_pragmatist": CustomerArchetype(
        archetype_id="value_conscious_pragmatist",
        name="Value-Conscious Pragmatist",
        description="Focused on practical value, price-quality tradeoffs, durability",
        psychological_dimensions={
            "price_sensitivity": 0.8,
            "practicality": 0.85,
            "brand_loyalty": 0.4,
            "impulse_tendency": 0.25,
            "research_tendency": 0.7,
        },
        mechanism_effectiveness={
            "value_proposition": 0.85,
            "social_proof": 0.7,
            "comparison": 0.75,
            "scarcity": 0.4,
            "emotional_appeal": 0.35,
            "authority": 0.6,
            "commitment": 0.65,
        },
        recommended_tone="informative",
        recommended_complexity="medium",
        recommended_frame="gain",
        sample_size=50000,
        confidence=0.8,
    ),
    
    "quality_seeker": CustomerArchetype(
        archetype_id="quality_seeker",
        name="Quality Seeker",
        description="Prioritizes quality, willing to pay premium, brand-conscious",
        psychological_dimensions={
            "price_sensitivity": 0.3,
            "quality_focus": 0.9,
            "brand_loyalty": 0.75,
            "impulse_tendency": 0.35,
            "research_tendency": 0.8,
        },
        mechanism_effectiveness={
            "authority": 0.85,
            "social_proof": 0.75,
            "quality_assurance": 0.9,
            "scarcity": 0.5,
            "value_proposition": 0.55,
            "emotional_appeal": 0.65,
            "exclusivity": 0.7,
        },
        recommended_tone="professional",
        recommended_complexity="high",
        recommended_frame="gain",
        sample_size=35000,
        confidence=0.8,
    ),
    
    "emotional_connector": CustomerArchetype(
        archetype_id="emotional_connector",
        name="Emotional Connector",
        description="Driven by emotional resonance, brand story, personal meaning",
        psychological_dimensions={
            "emotional_responsiveness": 0.9,
            "story_engagement": 0.85,
            "brand_attachment": 0.8,
            "impulse_tendency": 0.6,
            "social_identity": 0.75,
        },
        mechanism_effectiveness={
            "emotional_appeal": 0.9,
            "storytelling": 0.85,
            "nostalgia": 0.75,
            "social_proof": 0.7,
            "identity_appeal": 0.8,
            "authority": 0.45,
            "value_proposition": 0.4,
        },
        recommended_tone="warm",
        recommended_complexity="medium",
        recommended_frame="balanced",
        sample_size=42000,
        confidence=0.8,
    ),
    
    "skeptical_researcher": CustomerArchetype(
        archetype_id="skeptical_researcher",
        name="Skeptical Researcher",
        description="Distrustful of marketing, relies heavily on peer reviews, thorough researcher",
        psychological_dimensions={
            "skepticism": 0.85,
            "research_tendency": 0.95,
            "peer_reliance": 0.9,
            "impulse_tendency": 0.15,
            "brand_loyalty": 0.35,
        },
        mechanism_effectiveness={
            "social_proof": 0.85,
            "comparison": 0.8,
            "evidence": 0.9,
            "authority": 0.4,  # Low trust in authority
            "emotional_appeal": 0.25,  # Resistant
            "transparency": 0.85,
            "scarcity": 0.2,  # Sees through tactics
        },
        recommended_tone="factual",
        recommended_complexity="high",
        recommended_frame="loss",  # They respond to what to avoid
        sample_size=28000,
        confidence=0.8,
    ),
    
    "impulse_buyer": CustomerArchetype(
        archetype_id="impulse_buyer",
        name="Impulse Buyer",
        description="Makes quick decisions, susceptible to urgency, seeks instant gratification",
        psychological_dimensions={
            "impulse_tendency": 0.9,
            "delay_discounting": 0.85,
            "excitement_seeking": 0.75,
            "research_tendency": 0.2,
            "regret_tendency": 0.6,
        },
        mechanism_effectiveness={
            "scarcity": 0.9,
            "urgency": 0.85,
            "emotional_appeal": 0.8,
            "social_proof": 0.7,
            "impulse_trigger": 0.9,
            "value_proposition": 0.5,
            "comparison": 0.3,  # Don't slow them down
        },
        recommended_tone="exciting",
        recommended_complexity="simple",
        recommended_frame="gain",
        sample_size=31000,
        confidence=0.8,
    ),
    
    "loyal_advocate": CustomerArchetype(
        archetype_id="loyal_advocate",
        name="Loyal Advocate",
        description="Strong brand loyalty, frequent repeat purchaser, recommends to others",
        psychological_dimensions={
            "brand_loyalty": 0.95,
            "advocacy_tendency": 0.85,
            "relationship_value": 0.9,
            "price_sensitivity": 0.25,
            "openness_to_alternatives": 0.2,
        },
        mechanism_effectiveness={
            "loyalty_rewards": 0.9,
            "exclusivity": 0.8,
            "community": 0.85,
            "identity_appeal": 0.8,
            "comparison": 0.2,  # Don't compare, reinforce
            "new_features": 0.75,
            "appreciation": 0.85,
        },
        recommended_tone="appreciative",
        recommended_complexity="medium",
        recommended_frame="gain",
        sample_size=22000,
        confidence=0.85,
    ),
}


# =============================================================================
# SERVICE
# =============================================================================

class ArchetypeService:
    """
    Service for archetype-based fast path decisions.
    
    Provides:
    - Archetype matching for users/categories
    - Pre-computed mechanism weights for fast path
    - Archetype lookup from graph
    
    The archetypes represent validated patterns from:
    - Deep learning on 1B+ Amazon reviews
    - Outcome-validated mechanism effectiveness
    - Continuous learning updates
    """
    
    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
    ):
        self.driver = neo4j_driver
        
        # Local archetype registry
        self.archetypes = DEFAULT_ARCHETYPES.copy()
        
        logger.info(f"ArchetypeService initialized with {len(self.archetypes)} default archetypes")
    
    async def get_archetype(
        self,
        archetype_id: str,
    ) -> Optional[CustomerArchetype]:
        """Get archetype by ID."""
        
        # Check local registry
        if archetype_id in self.archetypes:
            return self.archetypes[archetype_id]
        
        # Try graph
        if self.driver:
            archetype = await self._query_archetype_from_graph(archetype_id)
            if archetype:
                self.archetypes[archetype_id] = archetype
                return archetype
        
        return None
    
    async def _query_archetype_from_graph(
        self,
        archetype_id: str,
    ) -> Optional[CustomerArchetype]:
        """Query archetype from Neo4j."""
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (a:CustomerArchetype {archetype_id: $archetype_id})
                    OPTIONAL MATCH (a)-[r:HAS_MECHANISM_EFFECTIVENESS]->(m:Mechanism)
                    RETURN a, 
                           COLLECT({mechanism: m.mechanism_id, effectiveness: r.effectiveness}) as mechanisms
                    """,
                    archetype_id=archetype_id
                )
                
                record = await result.single()
                if not record:
                    return None
                
                arch_data = record["a"]
                
                # Build mechanism effectiveness from relationships
                mech_effectiveness = {}
                for mech in record["mechanisms"]:
                    if mech["mechanism"]:
                        mech_effectiveness[mech["mechanism"]] = mech["effectiveness"] or 0.5
                
                archetype = CustomerArchetype(
                    archetype_id=archetype_id,
                    name=arch_data.get("name", archetype_id),
                    description=arch_data.get("description", ""),
                    psychological_dimensions=json.loads(arch_data.get("psychological_dimensions", "{}")),
                    mechanism_effectiveness=mech_effectiveness,
                    recommended_tone=arch_data.get("recommended_tone", "neutral"),
                    recommended_complexity=arch_data.get("recommended_complexity", "medium"),
                    recommended_frame=arch_data.get("recommended_frame", "balanced"),
                    sample_size=arch_data.get("sample_size", 0),
                    confidence=arch_data.get("confidence", 0.5),
                )
                
                return archetype
                
        except Exception as e:
            logger.error(f"Error querying archetype from graph: {e}")
            return None
    
    async def get_archetype_outputs(
        self,
        user_id: str,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get pre-computed outputs for archetype-based fast path.
        
        This is the main method used by the workflow's fast path.
        Returns atom-like outputs that can be used directly by synthesizer.
        """
        
        # Determine user's primary archetype
        archetype_id = await self._determine_user_archetype(user_id, category_id)
        archetype = await self.get_archetype(archetype_id)
        
        if not archetype:
            # Fallback to most common archetype
            archetype = self.archetypes.get("value_conscious_pragmatist")
        
        if not archetype:
            # Ultimate fallback
            return {"mechanism_weights": {}, "confidence": 0.3}
        
        # Build outputs in atom format
        outputs = {
            "atom_archetype_match": {
                "archetype_id": archetype.archetype_id,
                "archetype_name": archetype.name,
                "match_confidence": archetype.confidence,
            },
            "atom_mechanism_activation": {
                "mechanism_weights": archetype.mechanism_effectiveness,
                "source": "archetype_fast_path",
            },
            "atom_message_framing": {
                "recommended_frame": archetype.recommended_frame,
                "recommended_tone": archetype.recommended_tone,
                "recommended_complexity": archetype.recommended_complexity,
            },
        }
        
        return outputs
    
    async def _determine_user_archetype(
        self,
        user_id: str,
        category_id: Optional[str],
    ) -> str:
        """
        Determine the most likely archetype for a user.
        
        Uses:
        1. Graph-stored user archetype if available
        2. Category-based default archetype
        3. General default
        """
        
        # Try graph
        if self.driver:
            try:
                async with self.driver.session() as session:
                    result = await session.run(
                        """
                        MATCH (u:User {user_id: $user_id})-[r:MATCHES_ARCHETYPE]->(a:CustomerArchetype)
                        RETURN a.archetype_id as archetype_id, r.confidence as confidence
                        ORDER BY r.confidence DESC
                        LIMIT 1
                        """,
                        user_id=user_id
                    )
                    
                    record = await result.single()
                    if record and record["archetype_id"]:
                        return record["archetype_id"]
                        
            except Exception as e:
                logger.debug(f"Could not query user archetype: {e}")
        
        # Default to value_conscious_pragmatist (most common)
        return "value_conscious_pragmatist"
    
    async def update_archetype_effectiveness(
        self,
        archetype_id: str,
        mechanism_id: str,
        outcome_value: float,
        learning_rate: float = 0.01,
    ) -> None:
        """
        Update mechanism effectiveness for an archetype based on outcome.
        
        This is the learning integration point - called when outcomes are observed.
        """
        
        archetype = await self.get_archetype(archetype_id)
        if not archetype:
            return
        
        current = archetype.mechanism_effectiveness.get(mechanism_id, 0.5)
        
        # Exponential moving average update
        new_value = current + learning_rate * (outcome_value - current)
        
        archetype.mechanism_effectiveness[mechanism_id] = new_value
        
        # Persist to graph if available
        if self.driver:
            try:
                async with self.driver.session() as session:
                    await session.run(
                        """
                        MATCH (a:CustomerArchetype {archetype_id: $archetype_id})
                        MERGE (m:Mechanism {mechanism_id: $mechanism_id})
                        MERGE (a)-[r:HAS_MECHANISM_EFFECTIVENESS]->(m)
                        SET r.effectiveness = $effectiveness,
                            r.last_updated = datetime()
                        """,
                        archetype_id=archetype_id,
                        mechanism_id=mechanism_id,
                        effectiveness=new_value,
                    )
            except Exception as e:
                logger.error(f"Error updating archetype effectiveness: {e}")


# =============================================================================
# SINGLETON
# =============================================================================

_service: Optional[ArchetypeService] = None


def get_archetype_service(
    neo4j_driver: Optional[AsyncDriver] = None,
) -> ArchetypeService:
    """Get or create the archetype service singleton."""
    global _service
    
    if _service is None:
        _service = ArchetypeService(neo4j_driver=neo4j_driver)
    
    return _service
