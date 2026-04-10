# =============================================================================
# Brand Personality Graph Builder
# Location: adam/intelligence/knowledge_graph/brand_graph_builder.py
# =============================================================================

"""
BRAND PERSONALITY KNOWLEDGE GRAPH BUILDER

Stores Brand-as-Person profiles in Neo4j with rich relationships:

Nodes:
- :Brand - The brand entity with personality properties
- :BrandArchetype - Jung/Mark archetypes (12 types)
- :BrandRelationshipType - How brands relate to consumers
- :SocialSignal - What brand ownership signals

Relationships:
- (:Brand)-[:HAS_ARCHETYPE {confidence}]->(:BrandArchetype)
- (:Brand)-[:ATTRACTS {strength}]->(:CustomerArchetype)
- (:Brand)-[:HAS_RELATIONSHIP_STYLE]->(:BrandRelationshipType)
- (:Brand)-[:SIGNALS]->(:SocialSignal)
- (:Brand)-[:HAS_PRODUCT]->(:ScrapedProduct)
- (:Brand)-[:USES_MECHANISM {effectiveness}]->(:CognitiveMechanism)
- (:Brand)-[:FULFILLS_IDENTITY_NEED]->(:IdentityNeed)

Learning Relationships (updated from outcomes):
- (:Brand)-[:EFFECTIVENESS_WITH {score, trials}]->(:CustomerArchetype)
- (:Brand)-[:MECHANISM_SUCCESS {rate, trials}]->(:CognitiveMechanism)

This graph enables:
1. Brand-consumer compatibility queries
2. Mechanism selection based on brand personality
3. Learning from ad outcomes
4. Pattern discovery across brand-archetype combinations
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncDriver = Any

from adam.intelligence.models.brand_personality import (
    BrandPersonalityProfile,
    BrandArchetype,
    BrandRelationshipRole,
)


# =============================================================================
# CYPHER QUERIES
# =============================================================================

# Create or update Brand node
CREATE_BRAND_NODE = """
MERGE (b:Brand {brand_id: $brand_id})
SET b += $properties
SET b.updated_at = datetime()
RETURN b
"""

# Create BrandArchetype nodes (run once to populate)
CREATE_BRAND_ARCHETYPES = """
UNWIND $archetypes AS arch
MERGE (a:BrandArchetype {name: arch.name})
SET a.description = arch.description
SET a.core_desire = arch.core_desire
SET a.core_fear = arch.core_fear
RETURN count(a) as created
"""

# Create relationship between Brand and BrandArchetype
CREATE_BRAND_ARCHETYPE_REL = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (a:BrandArchetype {name: $archetype_name})
MERGE (b)-[r:HAS_ARCHETYPE]->(a)
SET r.confidence = $confidence
SET r.is_primary = $is_primary
RETURN r
"""

# Create relationship between Brand and CustomerArchetype (ATTRACTS)
CREATE_BRAND_ATTRACTS_REL = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (ca:CustomerArchetype {name: $archetype_name})
MERGE (b)-[r:ATTRACTS]->(ca)
SET r.strength = $strength
SET r.reasoning = $reasoning
RETURN r
"""

# Create relationship between Brand and CognitiveMechanism
CREATE_BRAND_MECHANISM_REL = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (m:CognitiveMechanism {name: $mechanism_name})
MERGE (b)-[r:USES_MECHANISM]->(m)
SET r.alignment = $alignment
SET r.is_preferred = $is_preferred
SET r.is_forbidden = $is_forbidden
RETURN r
"""

# Link Brand to Product
CREATE_BRAND_PRODUCT_REL = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (p:ScrapedProduct {product_id: $product_id})
MERGE (b)-[r:HAS_PRODUCT]->(p)
RETURN r
"""

# Query brand-user compatibility
QUERY_BRAND_USER_COMPATIBILITY = """
MATCH (b:Brand {brand_id: $brand_id})
OPTIONAL MATCH (b)-[attracts:ATTRACTS]->(ca:CustomerArchetype {name: $user_archetype})
OPTIONAL MATCH (b)-[arch:HAS_ARCHETYPE]->(ba:BrandArchetype)

// Get brand Big Five
WITH b, attracts, arch, ba,
     b.big_five_openness AS b_o,
     b.big_five_conscientiousness AS b_c,
     b.big_five_extraversion AS b_e,
     b.big_five_agreeableness AS b_a,
     b.big_five_neuroticism AS b_n

RETURN 
    b.brand_id AS brand_id,
    b.brand_name AS brand_name,
    b.brand_archetype AS brand_archetype,
    attracts.strength AS attraction_strength,
    arch.confidence AS archetype_confidence,
    {
        openness: b_o,
        conscientiousness: b_c,
        extraversion: b_e,
        agreeableness: b_a,
        neuroticism: b_n
    } AS brand_big_five,
    b.relationship_role AS relationship_role,
    b.social_signal AS social_signal
"""

# Query brand profile
QUERY_BRAND_PROFILE = """
MATCH (b:Brand {brand_id: $brand_id})
OPTIONAL MATCH (b)-[arch:HAS_ARCHETYPE]->(ba:BrandArchetype)
OPTIONAL MATCH (b)-[attracts:ATTRACTS]->(ca:CustomerArchetype)
OPTIONAL MATCH (b)-[uses:USES_MECHANISM]->(m:CognitiveMechanism)

RETURN b {
    .*,
    archetypes: collect(DISTINCT {
        name: ba.name, 
        confidence: arch.confidence, 
        is_primary: arch.is_primary
    }),
    attracts: collect(DISTINCT {
        archetype: ca.name, 
        strength: attracts.strength
    }),
    mechanisms: collect(DISTINCT {
        name: m.name, 
        alignment: uses.alignment, 
        preferred: uses.is_preferred
    })
} AS brand
"""

# Update brand effectiveness with archetype (from learning)
UPDATE_BRAND_ARCHETYPE_EFFECTIVENESS = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (ca:CustomerArchetype {name: $archetype_name})
MERGE (b)-[r:EFFECTIVENESS_WITH]->(ca)
SET r.trials = COALESCE(r.trials, 0) + 1
SET r.successes = COALESCE(r.successes, 0) + $success
SET r.effectiveness = toFloat(r.successes) / toFloat(r.trials)
SET r.updated_at = datetime()
RETURN r.effectiveness AS effectiveness, r.trials AS trials
"""

# Update brand mechanism success (from learning)
UPDATE_BRAND_MECHANISM_SUCCESS = """
MATCH (b:Brand {brand_id: $brand_id})
MATCH (m:CognitiveMechanism {name: $mechanism_name})
MERGE (b)-[r:MECHANISM_SUCCESS]->(m)
SET r.trials = COALESCE(r.trials, 0) + 1
SET r.successes = COALESCE(r.successes, 0) + $success
SET r.success_rate = toFloat(r.successes) / toFloat(r.trials)
SET r.updated_at = datetime()
RETURN r.success_rate AS success_rate, r.trials AS trials
"""

# Get brands that attract a specific archetype
QUERY_BRANDS_FOR_ARCHETYPE = """
MATCH (b:Brand)-[r:ATTRACTS]->(ca:CustomerArchetype {name: $archetype_name})
WHERE r.strength >= $min_strength
RETURN b.brand_id AS brand_id,
       b.brand_name AS brand_name,
       r.strength AS attraction_strength
ORDER BY r.strength DESC
LIMIT $limit
"""

# Get learned effectiveness patterns
QUERY_BRAND_EFFECTIVENESS_PATTERNS = """
MATCH (b:Brand)-[r:EFFECTIVENESS_WITH]->(ca:CustomerArchetype)
WHERE r.trials >= $min_trials
RETURN b.brand_archetype AS brand_archetype,
       ca.name AS customer_archetype,
       avg(r.effectiveness) AS avg_effectiveness,
       sum(r.trials) AS total_trials,
       count(b) AS brand_count
ORDER BY avg_effectiveness DESC
"""


# =============================================================================
# BRAND ARCHETYPE TAXONOMY
# =============================================================================

BRAND_ARCHETYPE_TAXONOMY = [
    {
        "name": "INNOCENT",
        "description": "Pure, optimistic, wholesome - wants to be happy",
        "core_desire": "To experience paradise",
        "core_fear": "Doing something wrong or bad",
    },
    {
        "name": "SAGE",
        "description": "Wise, knowledgeable, expert - seeks truth",
        "core_desire": "To understand the world",
        "core_fear": "Being misled or ignorant",
    },
    {
        "name": "EXPLORER",
        "description": "Adventurous, pioneering, independent",
        "core_desire": "Freedom to discover",
        "core_fear": "Being trapped or conforming",
    },
    {
        "name": "OUTLAW",
        "description": "Rebellious, disruptive, revolutionary",
        "core_desire": "Revenge or revolution",
        "core_fear": "Being powerless",
    },
    {
        "name": "MAGICIAN",
        "description": "Transformative, visionary, innovative",
        "core_desire": "To make dreams come true",
        "core_fear": "Unintended negative consequences",
    },
    {
        "name": "HERO",
        "description": "Courageous, determined, powerful",
        "core_desire": "To prove worth through achievement",
        "core_fear": "Weakness or vulnerability",
    },
    {
        "name": "LOVER",
        "description": "Passionate, sensual, intimate",
        "core_desire": "Intimacy and sensual pleasure",
        "core_fear": "Being unwanted or unloved",
    },
    {
        "name": "JESTER",
        "description": "Fun, playful, entertaining",
        "core_desire": "To live in the moment with joy",
        "core_fear": "Being boring or bored",
    },
    {
        "name": "EVERYMAN",
        "description": "Relatable, humble, authentic",
        "core_desire": "To belong and connect",
        "core_fear": "Standing out or being rejected",
    },
    {
        "name": "CAREGIVER",
        "description": "Nurturing, protective, supportive",
        "core_desire": "To protect and care for others",
        "core_fear": "Selfishness or ingratitude",
    },
    {
        "name": "RULER",
        "description": "Authoritative, premium, exclusive",
        "core_desire": "Control and order",
        "core_fear": "Chaos or being overthrown",
    },
    {
        "name": "CREATOR",
        "description": "Innovative, artistic, imaginative",
        "core_desire": "To create enduring value",
        "core_fear": "Mediocre vision or execution",
    },
]


# =============================================================================
# BRAND GRAPH BUILDER
# =============================================================================

class BrandGraphBuilder:
    """
    Builds and maintains brand personality knowledge in Neo4j.
    
    Responsibilities:
    1. Store brand personality profiles
    2. Create brand-archetype relationships
    3. Track brand-mechanism alignments
    4. Update effectiveness from learning
    5. Query brand-user compatibility
    """
    
    def __init__(self, driver: AsyncDriver):
        """
        Initialize with Neo4j driver.
        
        Args:
            driver: Neo4j async driver instance
        """
        self.driver = driver
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the graph with brand archetype taxonomy."""
        if self._initialized:
            return
        
        async with self.driver.session() as session:
            # Create BrandArchetype nodes
            await session.run(
                CREATE_BRAND_ARCHETYPES,
                archetypes=BRAND_ARCHETYPE_TAXONOMY
            )
            logger.info("Initialized brand archetype taxonomy in Neo4j")
        
        self._initialized = True
    
    async def store_brand_profile(
        self,
        profile: BrandPersonalityProfile,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store a brand personality profile in Neo4j.
        
        Creates:
        - Brand node with all properties
        - HAS_ARCHETYPE relationship to BrandArchetype
        - ATTRACTS relationships to CustomerArchetypes
        - USES_MECHANISM relationships to CognitiveMechanisms
        
        Args:
            profile: BrandPersonalityProfile to store
            product_id: Optional product ID to link
            
        Returns:
            Dict with storage results
        """
        await self.initialize()
        
        results = {
            "brand_id": profile.brand_id,
            "brand_name": profile.brand_name,
            "nodes_created": 0,
            "relationships_created": 0,
        }
        
        async with self.driver.session() as session:
            # 1. Create/update Brand node
            await session.run(
                CREATE_BRAND_NODE,
                brand_id=profile.brand_id,
                properties=profile.to_neo4j_properties(),
            )
            results["nodes_created"] += 1
            
            # 2. Create primary archetype relationship
            await session.run(
                CREATE_BRAND_ARCHETYPE_REL,
                brand_id=profile.brand_id,
                archetype_name=profile.brand_archetype.value.upper(),
                confidence=profile.brand_archetype_confidence,
                is_primary=True,
            )
            results["relationships_created"] += 1
            
            # 3. Create secondary archetype relationships
            for arch_name, confidence in profile.secondary_archetypes.items():
                try:
                    await session.run(
                        CREATE_BRAND_ARCHETYPE_REL,
                        brand_id=profile.brand_id,
                        archetype_name=arch_name.upper(),
                        confidence=confidence,
                        is_primary=False,
                    )
                    results["relationships_created"] += 1
                except Exception as e:
                    logger.warning(f"Could not create archetype rel for {arch_name}: {e}")
            
            # 4. Create ATTRACTS relationships
            for archetype in profile.attraction_dynamics.attracts_archetypes:
                strength = profile.attraction_dynamics.archetype_attraction_scores.get(
                    archetype, 0.7
                )
                try:
                    await session.run(
                        CREATE_BRAND_ATTRACTS_REL,
                        brand_id=profile.brand_id,
                        archetype_name=archetype.upper(),
                        strength=strength,
                        reasoning="",
                    )
                    results["relationships_created"] += 1
                except Exception as e:
                    logger.debug(f"Could not create attracts rel for {archetype}: {e}")
            
            # 5. Create mechanism relationships
            for mech in profile.mechanism_preferences.preferred_mechanisms:
                alignment = profile.mechanism_preferences.mechanism_alignment_scores.get(
                    mech, 0.8
                )
                try:
                    await session.run(
                        CREATE_BRAND_MECHANISM_REL,
                        brand_id=profile.brand_id,
                        mechanism_name=mech.upper(),
                        alignment=alignment,
                        is_preferred=True,
                        is_forbidden=False,
                    )
                    results["relationships_created"] += 1
                except Exception as e:
                    logger.debug(f"Could not create mechanism rel for {mech}: {e}")
            
            # 6. Create forbidden mechanism relationships
            for mech in profile.mechanism_preferences.forbidden_mechanisms:
                try:
                    await session.run(
                        CREATE_BRAND_MECHANISM_REL,
                        brand_id=profile.brand_id,
                        mechanism_name=mech.upper(),
                        alignment=0.1,
                        is_preferred=False,
                        is_forbidden=True,
                    )
                    results["relationships_created"] += 1
                except Exception as e:
                    logger.debug(f"Could not create forbidden mechanism rel for {mech}: {e}")
            
            # 7. Link to product if provided
            if product_id:
                try:
                    await session.run(
                        CREATE_BRAND_PRODUCT_REL,
                        brand_id=profile.brand_id,
                        product_id=product_id,
                    )
                    results["relationships_created"] += 1
                except Exception as e:
                    logger.debug(f"Could not link to product {product_id}: {e}")
        
        logger.info(
            f"Stored brand profile for {profile.brand_name}: "
            f"{results['nodes_created']} nodes, {results['relationships_created']} rels"
        )
        
        return results
    
    async def get_brand_profile(
        self,
        brand_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a brand profile from Neo4j.
        
        Args:
            brand_id: Brand ID
            
        Returns:
            Dict with brand data or None
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRAND_PROFILE,
                brand_id=brand_id,
            )
            record = await result.single()
            
            if record:
                return dict(record["brand"])
            return None
    
    async def get_brand_user_compatibility(
        self,
        brand_id: str,
        user_archetype: str,
        user_big_five: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Query brand-user compatibility from the graph.
        
        This is called by AdSelectionAtom to get brand_compatibility score.
        
        Args:
            brand_id: Brand ID
            user_archetype: User's archetype (e.g., "ACHIEVER")
            user_big_five: Optional user Big Five scores
            
        Returns:
            Dict with compatibility scores
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRAND_USER_COMPATIBILITY,
                brand_id=brand_id,
                user_archetype=user_archetype.upper(),
            )
            record = await result.single()
            
            if not record:
                return {"compatibility": 0.5, "found": False}
            
            # Base compatibility from attraction strength
            attraction = record["attraction_strength"] or 0.5
            
            # Adjust for Big Five similarity if provided
            personality_match = 0.5
            if user_big_five and record["brand_big_five"]:
                brand_b5 = record["brand_big_five"]
                diffs = []
                for trait in ["openness", "conscientiousness", "extraversion", "agreeableness"]:
                    if trait in user_big_five and brand_b5.get(trait):
                        diffs.append(abs(user_big_five[trait] - brand_b5[trait]))
                if diffs:
                    personality_match = 1.0 - (sum(diffs) / len(diffs))
            
            # Combined score
            compatibility = (attraction * 0.6) + (personality_match * 0.4)
            
            return {
                "compatibility": compatibility,
                "attraction_strength": attraction,
                "personality_match": personality_match,
                "brand_name": record["brand_name"],
                "brand_archetype": record["brand_archetype"],
                "relationship_role": record["relationship_role"],
                "social_signal": record["social_signal"],
                "found": True,
            }
    
    async def update_brand_archetype_effectiveness(
        self,
        brand_id: str,
        archetype_name: str,
        success: float,
    ) -> Dict[str, Any]:
        """
        Update brand-archetype effectiveness from an outcome.
        
        Called by Gradient Bridge when an ad outcome is received.
        
        Args:
            brand_id: Brand ID
            archetype_name: Customer archetype name
            success: 0.0-1.0 success value (usually 0 or 1)
            
        Returns:
            Dict with updated effectiveness
        """
        async with self.driver.session() as session:
            result = await session.run(
                UPDATE_BRAND_ARCHETYPE_EFFECTIVENESS,
                brand_id=brand_id,
                archetype_name=archetype_name.upper(),
                success=success,
            )
            record = await result.single()
            
            if record:
                logger.debug(
                    f"Updated brand {brand_id} effectiveness with {archetype_name}: "
                    f"{record['effectiveness']:.2%} ({record['trials']} trials)"
                )
                return {
                    "effectiveness": record["effectiveness"],
                    "trials": record["trials"],
                }
            return {"effectiveness": 0.5, "trials": 0}
    
    async def update_brand_mechanism_success(
        self,
        brand_id: str,
        mechanism_name: str,
        success: float,
    ) -> Dict[str, Any]:
        """
        Update brand-mechanism success rate from an outcome.
        
        Args:
            brand_id: Brand ID
            mechanism_name: Mechanism name
            success: 0.0-1.0 success value
            
        Returns:
            Dict with updated success rate
        """
        async with self.driver.session() as session:
            result = await session.run(
                UPDATE_BRAND_MECHANISM_SUCCESS,
                brand_id=brand_id,
                mechanism_name=mechanism_name.upper(),
                success=success,
            )
            record = await result.single()
            
            if record:
                return {
                    "success_rate": record["success_rate"],
                    "trials": record["trials"],
                }
            return {"success_rate": 0.5, "trials": 0}
    
    async def get_brands_for_archetype(
        self,
        archetype_name: str,
        min_strength: float = 0.6,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get brands that attract a specific consumer archetype.
        
        Args:
            archetype_name: Customer archetype name
            min_strength: Minimum attraction strength
            limit: Max results
            
        Returns:
            List of matching brands
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRANDS_FOR_ARCHETYPE,
                archetype_name=archetype_name.upper(),
                min_strength=min_strength,
                limit=limit,
            )
            records = await result.data()
            return records
    
    async def get_effectiveness_patterns(
        self,
        min_trials: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get learned effectiveness patterns across brand-archetype combinations.
        
        Used for pattern discovery and research validation.
        
        Args:
            min_trials: Minimum trials for statistical significance
            
        Returns:
            List of patterns with effectiveness data
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRAND_EFFECTIVENESS_PATTERNS,
                min_trials=min_trials,
            )
            records = await result.data()
            return records


# =============================================================================
# FACTORY
# =============================================================================

_brand_graph_builder: Optional[BrandGraphBuilder] = None


async def get_brand_graph_builder(driver: AsyncDriver) -> BrandGraphBuilder:
    """Get or create the brand graph builder."""
    global _brand_graph_builder
    if _brand_graph_builder is None:
        _brand_graph_builder = BrandGraphBuilder(driver)
        await _brand_graph_builder.initialize()
    return _brand_graph_builder
