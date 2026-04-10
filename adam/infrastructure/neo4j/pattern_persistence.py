# =============================================================================
# ADAM Graph Pattern Persistence
# Location: adam/infrastructure/neo4j/pattern_persistence.py
# =============================================================================

"""
GRAPH PATTERN PERSISTENCE

Stores persuasive patterns, templates, and effectiveness matrices from
review re-ingestion into Neo4j for real-time decision support.

This bridges the gap between offline intelligence extraction (re-ingestion)
and real-time decision making (atoms querying the graph).

Node Types Created:
- (:PersuasiveTemplate) - Language patterns that influence buyers
- (:MechanismEffectiveness) - Archetype → Mechanism success rates
- (:ProductIntelligence) - Per-product persuasion analysis
- (:BrandPersonality) - Brand Aaker personality profiles
- (:PurchaseJourney) - Co-purchase patterns (bought_together)

Relationships:
- (Archetype)-[:RESPONDS_TO]->(PersuasiveTemplate)
- (Archetype)-[:SUSCEPTIBLE_TO {rate}]->(Mechanism)
- (Brand)-[:HAS_PERSONALITY]->(BrandPersonality)
- (Product)-[:BOUGHT_WITH]->(Product)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class PatternSource(str, Enum):
    """Source of the pattern data."""
    REVIEW_INGESTION = "review_ingestion"
    BRAND_ANALYSIS = "brand_analysis"
    JOURNEY_ANALYSIS = "journey_analysis"
    RUNTIME_LEARNING = "runtime_learning"


@dataclass
class PersuasiveTemplateData:
    """A language pattern that influences purchase decisions."""
    pattern: str
    mechanism: str
    archetype: str
    category: str
    helpful_votes: int
    occurrence_count: int = 1
    success_rate: float = 0.0
    example_reviews: List[str] = None
    
    def __post_init__(self):
        if self.example_reviews is None:
            self.example_reviews = []


@dataclass
class EffectivenessData:
    """Archetype → Mechanism effectiveness rate."""
    archetype: str
    mechanism: str
    success_rate: float
    sample_size: int
    category: str = "all"
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


@dataclass
class JourneyData:
    """Co-purchase journey pattern."""
    source_asin: str
    target_asin: str
    bundle_frequency: int = 1
    category: str = ""
    journey_type: str = "co_purchase"  # co_purchase, upgrade, accessory


# =============================================================================
# PERSISTENCE SERVICE
# =============================================================================

class GraphPatternPersistence:
    """
    Persists persuasive intelligence to Neo4j for real-time access.
    
    This is the critical bridge between:
    - Offline: Re-ingestion extracts patterns from 1B+ reviews
    - Online: Atoms query these patterns during decisions
    
    Without this, re-ingestion results sit in JSON files and never
    power actual recommendations.
    """
    
    def __init__(self, neo4j_client=None):
        """
        Initialize with optional Neo4j client.
        
        If no client provided, will attempt to get singleton.
        """
        self._client = neo4j_client
        self._initialized = False
    
    async def _get_client(self):
        """Get or create Neo4j client."""
        if self._client:
            return self._client
        
        from adam.infrastructure.neo4j.client import get_neo4j_client
        self._client = get_neo4j_client()
        return self._client
    
    async def initialize_schema(self) -> bool:
        """
        Create indexes and constraints for pattern nodes.
        
        Should be called once during system startup or re-ingestion.
        """
        if self._initialized:
            return True
        
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                # Create constraints and indexes
                schema_queries = [
                    # Persuasive Template
                    """CREATE CONSTRAINT template_unique IF NOT EXISTS
                       FOR (t:PersuasiveTemplate) 
                       REQUIRE (t.pattern, t.archetype, t.mechanism) IS UNIQUE""",
                    
                    # Mechanism Effectiveness
                    """CREATE CONSTRAINT effectiveness_unique IF NOT EXISTS
                       FOR (e:MechanismEffectiveness)
                       REQUIRE (e.archetype, e.mechanism, e.category) IS UNIQUE""",
                    
                    # Product Intelligence
                    """CREATE CONSTRAINT product_intel_unique IF NOT EXISTS
                       FOR (p:ProductIntelligence)
                       REQUIRE p.asin IS UNIQUE""",
                    
                    # Brand Personality
                    """CREATE CONSTRAINT brand_personality_unique IF NOT EXISTS
                       FOR (b:BrandPersonality)
                       REQUIRE b.brand IS UNIQUE""",
                    
                    # Indexes for fast lookups
                    """CREATE INDEX template_archetype IF NOT EXISTS
                       FOR (t:PersuasiveTemplate) ON (t.archetype)""",
                    
                    """CREATE INDEX template_mechanism IF NOT EXISTS
                       FOR (t:PersuasiveTemplate) ON (t.mechanism)""",
                    
                    """CREATE INDEX effectiveness_archetype IF NOT EXISTS
                       FOR (e:MechanismEffectiveness) ON (e.archetype)""",
                    
                    """CREATE INDEX product_brand IF NOT EXISTS
                       FOR (p:ProductIntelligence) ON (p.brand)""",
                    
                    """CREATE INDEX product_category IF NOT EXISTS
                       FOR (p:ProductIntelligence) ON (p.category)""",
                    
                    # ---- Corpus Fusion Entities (Phase 5) ----
                    
                    # CorpusPrior — empirical mechanism priors per category × archetype
                    """CREATE CONSTRAINT corpus_prior_unique IF NOT EXISTS
                       FOR (cp:CorpusPrior)
                       REQUIRE (cp.category, cp.archetype) IS UNIQUE""",
                    
                    """CREATE INDEX corpus_prior_category IF NOT EXISTS
                       FOR (cp:CorpusPrior) ON (cp.category)""",
                    
                    # PlatformCalibration — per-platform adjustment factors
                    """CREATE CONSTRAINT platform_cal_unique IF NOT EXISTS
                       FOR (pc:PlatformCalibration)
                       REQUIRE (pc.platform, pc.mechanism, pc.category) IS UNIQUE""",
                    
                    """CREATE INDEX platform_cal_platform IF NOT EXISTS
                       FOR (pc:PlatformCalibration) ON (pc.platform)""",
                    
                    # ResonanceTemplate — helpful-vote-validated persuasion patterns
                    """CREATE CONSTRAINT resonance_tmpl_unique IF NOT EXISTS
                       FOR (rt:ResonanceTemplate)
                       REQUIRE rt.template_id IS UNIQUE""",
                    
                    """CREATE INDEX resonance_tmpl_mechanism IF NOT EXISTS
                       FOR (rt:ResonanceTemplate) ON (rt.mechanism)""",
                    
                    """CREATE INDEX resonance_tmpl_category IF NOT EXISTS
                       FOR (rt:ResonanceTemplate) ON (rt.category)""",
                    
                    # TraitCategoryBridge — trait → category transfer edges
                    """CREATE INDEX trait_bridge_trait IF NOT EXISTS
                       FOR (tb:TraitCategoryBridge) ON (tb.trait)""",
                ]
                
                for query in schema_queries:
                    try:
                        await session.run(query)
                    except Exception as e:
                        # Ignore "already exists" errors
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Schema query failed: {e}")
                
                self._initialized = True
                logger.info("Graph pattern schema initialized")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize pattern schema: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # TEMPLATE PERSISTENCE
    # -------------------------------------------------------------------------
    
    async def store_templates(
        self,
        templates: List[PersuasiveTemplateData],
        source: PatternSource = PatternSource.REVIEW_INGESTION,
    ) -> int:
        """
        Store persuasive language templates into Neo4j.
        
        These templates are extracted from high-helpful-vote reviews
        and represent language that actually persuades real buyers.
        
        Args:
            templates: List of template data
            source: Where this data came from
            
        Returns:
            Number of templates stored
        """
        if not templates:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                
                stored = 0
                batch_size = 100
                
                for i in range(0, len(templates), batch_size):
                    batch = templates[i:i + batch_size]
                    
                    # Batch MERGE for efficiency
                    query = """
                    UNWIND $templates AS t
                    MERGE (pt:PersuasiveTemplate {
                        pattern: t.pattern,
                        archetype: t.archetype,
                        mechanism: t.mechanism
                    })
                    ON CREATE SET
                        pt.category = t.category,
                        pt.helpful_votes = t.helpful_votes,
                        pt.occurrence_count = t.occurrence_count,
                        pt.success_rate = t.success_rate,
                        pt.source = $source,
                        pt.created_at = datetime(),
                        pt.updated_at = datetime()
                    ON MATCH SET
                        pt.helpful_votes = pt.helpful_votes + t.helpful_votes,
                        pt.occurrence_count = pt.occurrence_count + t.occurrence_count,
                        pt.updated_at = datetime()
                    
                    // Link to archetype node if exists
                    WITH pt, t
                    OPTIONAL MATCH (a:Archetype {name: t.archetype})
                    FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (a)-[:RESPONDS_TO]->(pt)
                    )
                    
                    // Link to mechanism node if exists
                    WITH pt, t
                    OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: t.mechanism})
                    FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (pt)-[:USES_MECHANISM]->(m)
                    )
                    
                    RETURN count(pt) AS stored
                    """
                    
                    template_dicts = [
                        {
                            "pattern": t.pattern,
                            "archetype": t.archetype,
                            "mechanism": t.mechanism,
                            "category": t.category,
                            "helpful_votes": t.helpful_votes,
                            "occurrence_count": t.occurrence_count,
                            "success_rate": t.success_rate,
                        }
                        for t in batch
                    ]
                    
                    result = await session.run(
                        query,
                        templates=template_dicts,
                        source=source.value,
                    )
                    record = await result.single()
                    stored += record["stored"] if record else 0
                
                logger.info(f"Stored {stored} persuasive templates")
                return stored
                
        except Exception as e:
            logger.error(f"Failed to store templates: {e}")
            return 0
    
    # -------------------------------------------------------------------------
    # EFFECTIVENESS PERSISTENCE
    # -------------------------------------------------------------------------
    
    async def store_effectiveness_matrix(
        self,
        effectiveness_data: Dict[str, Dict[str, Dict[str, Any]]],
        category: str = "all",
    ) -> int:
        """
        Store archetype → mechanism effectiveness rates.
        
        This is the core intelligence: which persuasion mechanisms
        work best for which customer archetypes.
        
        Args:
            effectiveness_data: {archetype: {mechanism: {success_rate, sample_size}}}
            category: Product category (or "all" for aggregate)
            
        Returns:
            Number of effectiveness records stored
        """
        if not effectiveness_data:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                
                stored = 0
                
                for archetype, mechanisms in effectiveness_data.items():
                    for mechanism, stats in mechanisms.items():
                        success_rate = stats.get("success_rate", 0.0)
                        sample_size = stats.get("sample_size", 0)
                        
                        if sample_size < 10:  # Skip low-confidence data
                            continue
                        
                        query = """
                        MERGE (e:MechanismEffectiveness {
                            archetype: $archetype,
                            mechanism: $mechanism,
                            category: $category
                        })
                        ON CREATE SET
                            e.success_rate = $success_rate,
                            e.sample_size = $sample_size,
                            e.created_at = datetime(),
                            e.updated_at = datetime()
                        ON MATCH SET
                            // Weighted average with existing data
                            e.success_rate = (e.success_rate * e.sample_size + $success_rate * $sample_size) 
                                           / (e.sample_size + $sample_size),
                            e.sample_size = e.sample_size + $sample_size,
                            e.updated_at = datetime()
                        
                        // Create/update relationship to archetype
                        WITH e
                        OPTIONAL MATCH (a:Archetype {name: $archetype})
                        OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: $mechanism})
                        FOREACH (_ IN CASE WHEN a IS NOT NULL AND m IS NOT NULL THEN [1] ELSE [] END |
                            MERGE (a)-[r:SUSCEPTIBLE_TO]->(m)
                            ON CREATE SET r.rate = $success_rate, r.samples = $sample_size
                            ON MATCH SET 
                                r.rate = (r.rate * r.samples + $success_rate * $sample_size) / (r.samples + $sample_size),
                                r.samples = r.samples + $sample_size
                        )
                        
                        RETURN e
                        """
                        
                        await session.run(
                            query,
                            archetype=archetype,
                            mechanism=mechanism,
                            category=category,
                            success_rate=success_rate,
                            sample_size=sample_size,
                        )
                        stored += 1
                
                logger.info(f"Stored {stored} effectiveness records")
                return stored
                
        except Exception as e:
            logger.error(f"Failed to store effectiveness matrix: {e}")
            return 0
    
    # -------------------------------------------------------------------------
    # PRODUCT INTELLIGENCE PERSISTENCE
    # -------------------------------------------------------------------------
    
    async def store_product_intelligence(
        self,
        asin: str,
        brand: str,
        category: str,
        intelligence: Dict[str, Any],
    ) -> bool:
        """
        Store per-product persuasion intelligence.
        
        This includes:
        - Cialdini principle scores extracted from brand copy
        - Aaker personality scores
        - High-influence review count
        - Dominant persuasion tactics
        
        Args:
            asin: Product ASIN
            brand: Brand name
            category: Product category
            intelligence: Dict with cialdini_scores, aaker_scores, tactics, etc.
            
        Returns:
            True if stored successfully
        """
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                
                query = """
                MERGE (p:ProductIntelligence {asin: $asin})
                SET
                    p.brand = $brand,
                    p.category = $category,
                    p.cialdini_scores = $cialdini_scores,
                    p.aaker_scores = $aaker_scores,
                    p.primary_personality = $primary_personality,
                    p.tactics = $tactics,
                    p.high_influence_reviews = $high_influence_reviews,
                    p.total_reviews = $total_reviews,
                    p.avg_helpful_votes = $avg_helpful_votes,
                    p.updated_at = datetime()
                
                // Link to brand if exists
                WITH p
                OPTIONAL MATCH (b:Brand {name: $brand})
                FOREACH (_ IN CASE WHEN b IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (p)-[:BELONGS_TO]->(b)
                )
                
                RETURN p
                """
                
                await session.run(
                    query,
                    asin=asin,
                    brand=brand,
                    category=category,
                    cialdini_scores=intelligence.get("cialdini_scores", {}),
                    aaker_scores=intelligence.get("aaker_scores", {}),
                    primary_personality=intelligence.get("primary_personality", ""),
                    tactics=intelligence.get("tactics", []),
                    high_influence_reviews=intelligence.get("high_influence_reviews", 0),
                    total_reviews=intelligence.get("total_reviews", 0),
                    avg_helpful_votes=intelligence.get("avg_helpful_votes", 0.0),
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store product intelligence: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # JOURNEY PERSISTENCE
    # -------------------------------------------------------------------------
    
    async def store_journey_patterns(
        self,
        journeys: List[JourneyData],
    ) -> int:
        """
        Store co-purchase journey patterns from bought_together data.
        
        This enables cross-product recommendations and journey intelligence.
        
        Args:
            journeys: List of journey data
            
        Returns:
            Number of journey patterns stored
        """
        if not journeys:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                
                stored = 0
                batch_size = 100
                
                for i in range(0, len(journeys), batch_size):
                    batch = journeys[i:i + batch_size]
                    
                    query = """
                    UNWIND $journeys AS j
                    
                    // Ensure both products exist
                    MERGE (source:ProductIntelligence {asin: j.source_asin})
                    MERGE (target:ProductIntelligence {asin: j.target_asin})
                    
                    // Create journey relationship
                    MERGE (source)-[r:BOUGHT_WITH]->(target)
                    ON CREATE SET
                        r.frequency = j.bundle_frequency,
                        r.journey_type = j.journey_type,
                        r.category = j.category,
                        r.created_at = datetime()
                    ON MATCH SET
                        r.frequency = r.frequency + j.bundle_frequency,
                        r.updated_at = datetime()
                    
                    RETURN count(r) AS stored
                    """
                    
                    journey_dicts = [
                        {
                            "source_asin": j.source_asin,
                            "target_asin": j.target_asin,
                            "bundle_frequency": j.bundle_frequency,
                            "journey_type": j.journey_type,
                            "category": j.category,
                        }
                        for j in batch
                    ]
                    
                    result = await session.run(query, journeys=journey_dicts)
                    record = await result.single()
                    stored += record["stored"] if record else 0
                
                logger.info(f"Stored {stored} journey patterns")
                return stored
                
        except Exception as e:
            logger.error(f"Failed to store journey patterns: {e}")
            return 0
    
    # -------------------------------------------------------------------------
    # QUERY METHODS (for atoms to use)
    # -------------------------------------------------------------------------
    
    async def get_best_templates_for_archetype(
        self,
        archetype: str,
        mechanism: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get the most effective persuasive templates for an archetype.
        
        Used by atoms during decision-making to craft messages.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                
                if mechanism:
                    query = """
                    MATCH (t:PersuasiveTemplate {archetype: $archetype, mechanism: $mechanism})
                    RETURN t.pattern AS pattern, 
                           t.helpful_votes AS votes,
                           t.mechanism AS mechanism,
                           t.success_rate AS success_rate
                    ORDER BY t.helpful_votes DESC
                    LIMIT $limit
                    """
                    result = await session.run(
                        query,
                        archetype=archetype,
                        mechanism=mechanism,
                        limit=limit,
                    )
                else:
                    query = """
                    MATCH (t:PersuasiveTemplate {archetype: $archetype})
                    RETURN t.pattern AS pattern,
                           t.helpful_votes AS votes,
                           t.mechanism AS mechanism,
                           t.success_rate AS success_rate
                    ORDER BY t.helpful_votes DESC
                    LIMIT $limit
                    """
                    result = await session.run(
                        query,
                        archetype=archetype,
                        limit=limit,
                    )
                
                templates = []
                async for record in result:
                    templates.append(dict(record))
                
                return templates
                
        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return []
    
    async def get_mechanism_effectiveness(
        self,
        archetype: str,
        category: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get mechanism effectiveness rates for an archetype.
        
        Used by atoms to select the best persuasion mechanism.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                
                query = """
                MATCH (e:MechanismEffectiveness {archetype: $archetype})
                WHERE e.category = $category OR e.category = 'all'
                RETURN e.mechanism AS mechanism,
                       e.success_rate AS rate,
                       e.sample_size AS samples
                ORDER BY e.success_rate DESC
                """
                
                result = await session.run(
                    query,
                    archetype=archetype,
                    category=category or "all",
                )
                
                effectiveness = {}
                async for record in result:
                    effectiveness[record["mechanism"]] = record["rate"]
                
                return effectiveness
                
        except Exception as e:
            logger.error(f"Failed to get effectiveness: {e}")
            return {}
    
    async def get_product_intelligence(
        self,
        asin: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get pre-computed intelligence for a product.
        
        Used during decision-making to understand brand persuasion tactics.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                
                query = """
                MATCH (p:ProductIntelligence {asin: $asin})
                RETURN p {.*} AS intel
                """
                
                result = await session.run(query, asin=asin)
                record = await result.single()
                
                if record:
                    return dict(record["intel"])
                return None
                
        except Exception as e:
            logger.error(f"Failed to get product intelligence: {e}")
            return None
    
    async def get_journey_products(
        self,
        asin: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get products frequently bought with this one.
        
        Used for cross-product recommendations.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                
                query = """
                MATCH (source:ProductIntelligence {asin: $asin})-[r:BOUGHT_WITH]->(target)
                RETURN target.asin AS asin,
                       target.brand AS brand,
                       r.frequency AS frequency,
                       r.journey_type AS journey_type
                ORDER BY r.frequency DESC
                LIMIT $limit
                """
                
                result = await session.run(query, asin=asin, limit=limit)
                
                products = []
                async for record in result:
                    products.append(dict(record))
                
                return products
                
        except Exception as e:
            logger.error(f"Failed to get journey products: {e}")
            return []
    
    # -------------------------------------------------------------------------
    # DSP GRAPH QUERY METHODS
    # These query the DSPConstruct, BehavioralSignal, and relationship edges
    # persisted by scripts/populate_neo4j_graph.py (Phase 1a of Runtime Integration)
    # -------------------------------------------------------------------------
    
    async def get_dsp_empirical_effectiveness(
        self,
        archetype: str,
        limit: int = 20,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get empirical effectiveness data from EMPIRICALLY_EFFECTIVE edges.
        
        Queries archetype→mechanism effectiveness with success_rate and sample_size
        from the 937M+ review corpus. Returns richer data than get_mechanism_effectiveness
        because it includes sample_size for confidence weighting.
        
        Returns: {mechanism_id: {success_rate, sample_size, categories_seen}}
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                query = """
                MATCH (a:DSPConstruct)-[r:EMPIRICALLY_EFFECTIVE]->(m:DSPConstruct)
                WHERE a.construct_id CONTAINS $archetype
                RETURN m.construct_id AS mechanism,
                       r.success_rate AS success_rate,
                       r.sample_size AS sample_size,
                       r.categories_seen AS categories_seen,
                       r.description AS description
                ORDER BY r.success_rate DESC
                LIMIT $limit
                """
                result = await session.run(query, archetype=archetype, limit=limit)
                
                effectiveness = {}
                async for record in result:
                    effectiveness[record["mechanism"]] = {
                        "success_rate": record["success_rate"] or 0.0,
                        "sample_size": record["sample_size"] or 0,
                        "categories_seen": record["categories_seen"] or "",
                        "description": record["description"] or "",
                    }
                
                return effectiveness
                
        except Exception as e:
            logger.debug(f"Failed to get DSP empirical effectiveness: {e}")
            return {}
    
    async def get_dsp_alignment_edges(
        self,
        source_id: str,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get alignment matrix edges for a source construct (motivation, decision style, etc.)
        
        Queries all 7 alignment relationship types:
        ALIGNS_WITH_VALUE, RESPONDS_TO_STYLE, RESONATES_WITH_EMOTION,
        PREFERS_PERSONALITY, SUSCEPTIBLE_TO, MATCHES_COMPLEXITY, RESPONDS_TO_TECHNIQUE
        
        Returns: [{edge_type, target_id, strength, matrix, description}]
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                query = """
                MATCH (s:DSPConstruct {construct_id: $source_id})-[r]->(t:DSPConstruct)
                WHERE type(r) IN [
                    'ALIGNS_WITH_VALUE', 'RESPONDS_TO_STYLE', 'RESONATES_WITH_EMOTION',
                    'PREFERS_PERSONALITY', 'SUSCEPTIBLE_TO', 'MATCHES_COMPLEXITY',
                    'RESPONDS_TO_TECHNIQUE'
                ]
                RETURN type(r) AS edge_type,
                       t.construct_id AS target_id,
                       t.name AS target_name,
                       r.strength AS strength,
                       r.matrix AS matrix,
                       r.description AS description
                ORDER BY r.strength DESC
                LIMIT $limit
                """
                result = await session.run(query, source_id=source_id, limit=limit)
                
                edges = []
                async for record in result:
                    edges.append({
                        "edge_type": record["edge_type"],
                        "target_id": record["target_id"],
                        "target_name": record["target_name"],
                        "strength": record["strength"] or 0.0,
                        "matrix": record["matrix"] or "",
                        "description": record["description"] or "",
                    })
                
                return edges
                
        except Exception as e:
            logger.debug(f"Failed to get DSP alignment edges: {e}")
            return []
    
    async def get_dsp_category_moderation(
        self,
        category: str,
        limit: int = 15,
    ) -> Dict[str, float]:
        """
        Get category-specific mechanism moderation deltas from CONTEXTUALLY_MODERATES edges.
        
        Returns: {mechanism_id: delta} where delta is positive (boost) or negative (dampen)
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                # Try exact match first, then substring
                query = """
                MATCH (c:DSPConstruct)-[r:CONTEXTUALLY_MODERATES]->(m:DSPConstruct)
                WHERE c.construct_id = $cat_id OR c.construct_id CONTAINS $cat_lower
                RETURN m.construct_id AS mechanism,
                       r.strength AS delta,
                       r.description AS description
                LIMIT $limit
                """
                # Normalize category to DSP construct ID format
                cat_id = f"cat_{category.lower().replace(' ', '_').replace('&', '_')}"
                
                result = await session.run(
                    query, cat_id=cat_id, cat_lower=category.lower(), limit=limit
                )
                
                moderation = {}
                async for record in result:
                    moderation[record["mechanism"]] = record["delta"] or 0.0
                
                return moderation
                
        except Exception as e:
            logger.debug(f"Failed to get DSP category moderation: {e}")
            return {}
    
    async def get_dsp_relationship_amplification(
        self,
        relationship_type: str,
        limit: int = 10,
    ) -> Dict[str, float]:
        """
        Get mechanism amplification boosts from brand-consumer relationship MODERATES edges.
        
        Returns: {mechanism_id: boost_factor}
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                query = """
                MATCH (rel:DSPConstruct {construct_id: $rel_id})-[r:MODERATES]->(m:DSPConstruct)
                RETURN m.construct_id AS mechanism,
                       r.strength AS boost,
                       r.description AS description
                LIMIT $limit
                """
                rel_id = relationship_type.lower().replace(" ", "_")
                
                result = await session.run(query, rel_id=rel_id, limit=limit)
                
                amplification = {}
                async for record in result:
                    amplification[record["mechanism"]] = record["boost"] or 1.0
                
                return amplification
                
        except Exception as e:
            logger.debug(f"Failed to get DSP relationship amplification: {e}")
            return {}
    
    async def get_dsp_mechanism_susceptibility(
        self,
        decision_style: str,
        limit: int = 10,
    ) -> Dict[str, float]:
        """
        Get mechanism susceptibility scores for a decision style from SUSCEPTIBLE_TO edges.
        
        Returns: {mechanism_id: susceptibility_strength}
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                # Try both with and without ds_ prefix (graph may store either form)
                query = """
                MATCH (ds:DSPConstruct)-[r:SUSCEPTIBLE_TO]->(m:DSPConstruct)
                WHERE ds.construct_id = $ds_id OR ds.construct_id = $ds_id_alt
                RETURN m.construct_id AS mechanism,
                       r.strength AS strength,
                       r.description AS description
                ORDER BY r.strength DESC
                LIMIT $limit
                """
                if decision_style.startswith("ds_"):
                    ds_id = decision_style
                    ds_id_alt = decision_style[3:]  # strip ds_ prefix
                else:
                    ds_id = f"ds_{decision_style}"
                    ds_id_alt = decision_style
                
                result = await session.run(query, ds_id=ds_id, ds_id_alt=ds_id_alt, limit=limit)
                
                susceptibility = {}
                async for record in result:
                    susceptibility[record["mechanism"]] = record["strength"] or 0.0
                
                return susceptibility
                
        except Exception as e:
            logger.debug(f"Failed to get DSP mechanism susceptibility: {e}")
            return {}
    
    async def get_dsp_construct(
        self,
        construct_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single DSPConstruct node by ID.
        
        Returns: {construct_id, name, domain, description, confidence, ...}
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()
            
            async with await client.session() as session:
                query = """
                MATCH (c:DSPConstruct {construct_id: $id})
                RETURN c {.*} AS construct
                """
                result = await session.run(query, id=construct_id)
                record = await result.single()
                
                if record:
                    return dict(record["construct"])
                return None
                
        except Exception as e:
            logger.debug(f"Failed to get DSP construct: {e}")
            return None

    # =========================================================================
    # DSP MULTI-HOP & NEIGHBORHOOD QUERIES
    # =========================================================================

    async def get_construct_neighborhood(
        self,
        construct_id: str,
        max_hops: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get all DSP constructs within N hops of the given construct.

        Returns a list of {construct_id, name, domain, distance, path_type}
        for all reachable constructs up to max_hops away.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()

            async with await client.session() as session:
                query = f"""
                MATCH (start:DSPConstruct {{construct_id: $id}})
                MATCH path = (start)-[*1..{min(max_hops, 4)}]-(neighbor:DSPConstruct)
                WHERE neighbor.construct_id <> $id
                WITH neighbor, length(path) AS distance,
                     [r IN relationships(path) | type(r)] AS edge_types
                RETURN DISTINCT
                    neighbor.construct_id AS construct_id,
                    neighbor.name AS name,
                    neighbor.domain AS domain,
                    min(distance) AS distance,
                    collect(DISTINCT edge_types)[0] AS path_types
                ORDER BY distance, neighbor.name
                LIMIT $limit
                """
                result = await session.run(query, id=construct_id, limit=limit)
                records = await result.data()
                return [dict(r) for r in records]

        except Exception as e:
            logger.debug(f"Failed to get construct neighborhood: {e}")
            return []

    async def get_inferential_chain(
        self,
        source_id: str,
        target_mechanism: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find inferential chains from a signal/construct to a mechanism.

        Returns paths like:
          BehavioralSignal -> DSPConstruct -> DSPConstruct -> CognitiveMechanism
          or DSPConstruct -> DSPConstruct -> DSPConstruct (mechanism edge)

        Each result: {chain: [{node_id, node_type, name}], edges: [type], total_strength}
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()

            async with await client.session() as session:
                query = f"""
                MATCH path = (start {{construct_id: $source}})-[rels*1..{min(max_depth, 4)}]->(endNode:DSPConstruct)
                WHERE any(r IN rels WHERE r.mechanism = $mechanism)
                WITH path, rels,
                     reduce(s = 1.0, r IN rels | s * coalesce(r.strength, 0.5)) AS total_strength
                RETURN
                    [n IN nodes(path) |
                        CASE
                            WHEN n:BehavioralSignal THEN {{id: n.signal_id, type: 'signal', name: n.name}}
                            ELSE {{id: n.construct_id, type: 'construct', name: n.name}}
                        END
                    ] AS chain,
                    [r IN rels | type(r)] AS edges,
                    total_strength
                ORDER BY total_strength DESC
                LIMIT 5
                """
                result = await session.run(
                    query, source=source_id, mechanism=target_mechanism
                )
                records = await result.data()
                return [dict(r) for r in records]

        except Exception as e:
            logger.debug(f"Failed to get inferential chain: {e}")
            return []

    async def get_construct_creative_implications(
        self,
        construct_id: str,
    ) -> Dict[str, Any]:
        """
        Get creative_implications from a construct node and its connected edges.

        Returns combined creative implications from:
        1. The construct node's own creative_implications property
        2. The creative_implications from edges connected to this construct
        """
        try:
            import json as _json

            client = await self._get_client()
            if not client.is_connected:
                await client.connect()

            async with await client.session() as session:
                query = """
                MATCH (c:DSPConstruct {construct_id: $id})
                OPTIONAL MATCH (c)-[r]-()
                WHERE r.creative_implications IS NOT NULL AND r.creative_implications <> '{}'
                RETURN
                    c.creative_implications AS node_implications,
                    collect(DISTINCT {
                        edge_type: type(r),
                        mechanism: r.mechanism,
                        implications: r.creative_implications
                    }) AS edge_implications
                """
                result = await session.run(query, id=construct_id)
                record = await result.single()

                if not record:
                    return {}

                combined = {}

                # Parse node-level implications
                node_ci = record.get("node_implications", "{}")
                if node_ci and node_ci != "{}":
                    try:
                        combined["construct"] = _json.loads(node_ci)
                    except (TypeError, _json.JSONDecodeError):
                        combined["construct"] = node_ci

                # Parse edge-level implications
                edge_impls = record.get("edge_implications", [])
                edge_list = []
                for ei in edge_impls:
                    if ei and ei.get("implications"):
                        try:
                            parsed = _json.loads(ei["implications"])
                        except (TypeError, _json.JSONDecodeError):
                            parsed = ei["implications"]
                        edge_list.append({
                            "edge_type": ei.get("edge_type"),
                            "mechanism": ei.get("mechanism"),
                            "implications": parsed,
                        })
                if edge_list:
                    combined["edges"] = edge_list

                return combined

        except Exception as e:
            logger.debug(f"Failed to get creative implications: {e}")
            return {}

    async def get_constructs_by_domain(
        self,
        domain: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Browse DSP constructs by psychological domain.

        Returns list of {construct_id, name, domain, description, confidence}.
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()

            async with await client.session() as session:
                query = """
                MATCH (c:DSPConstruct)
                WHERE toLower(c.domain) = toLower($domain)
                RETURN c.construct_id AS construct_id,
                       c.name AS name,
                       c.domain AS domain,
                       c.description AS description,
                       c.confidence AS confidence
                ORDER BY c.name
                LIMIT $limit
                """
                result = await session.run(query, domain=domain, limit=limit)
                records = await result.data()
                return [dict(r) for r in records]

        except Exception as e:
            logger.debug(f"Failed to browse constructs by domain: {e}")
            return []

    async def get_constructs_for_mechanism(
        self,
        mechanism: str,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Get all DSP constructs connected to a mechanism via any edge.

        Useful for construct-level credit attribution: given a mechanism
        that succeeded/failed, find which constructs are connected.

        Returns: [{construct_id, name, domain, edge_type, strength}]
        """
        try:
            client = await self._get_client()
            if not client.is_connected:
                await client.connect()

            async with await client.session() as session:
                query = """
                MATCH (c:DSPConstruct)-[r]-(other:DSPConstruct)
                WHERE r.mechanism = $mechanism
                RETURN DISTINCT
                    c.construct_id AS construct_id,
                    c.name AS name,
                    c.domain AS domain,
                    type(r) AS edge_type,
                    r.strength AS strength
                ORDER BY r.strength DESC
                LIMIT $limit
                """
                result = await session.run(query, mechanism=mechanism, limit=limit)
                records = await result.data()
                return [dict(r) for r in records]

        except Exception as e:
            logger.debug(f"Failed to get constructs for mechanism: {e}")
            return []


    # =========================================================================
    # CORPUS FUSION: STORE CORPUS PRIORS
    # =========================================================================
    
    async def store_corpus_priors(
        self,
        priors: List[Dict[str, Any]],
    ) -> int:
        """
        Store corpus-derived mechanism priors as first-class Neo4j nodes.
        
        Each CorpusPrior node represents the empirical effectiveness distribution
        of mechanisms for a given category × archetype, derived from 1B+ reviews.
        
        Args:
            priors: List of dicts with keys:
                category, archetype, mechanism_priors (dict), confidence,
                total_evidence, transfer_sources (list)
        
        Returns:
            Number of priors stored
        """
        if not priors:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                stored = 0
                batch_size = 50
                
                for i in range(0, len(priors), batch_size):
                    batch = priors[i:i + batch_size]
                    
                    query = """
                    UNWIND $priors AS p
                    MERGE (cp:CorpusPrior {
                        category: p.category,
                        archetype: p.archetype
                    })
                    SET cp.mechanism_priors = p.mechanism_priors_json,
                        cp.confidence = p.confidence,
                        cp.total_evidence = p.total_evidence,
                        cp.transfer_sources = p.transfer_sources,
                        cp.source = 'corpus_fusion',
                        cp.updated_at = datetime()
                    
                    // Link to archetype node if exists
                    WITH cp, p
                    OPTIONAL MATCH (a:Archetype {name: p.archetype})
                    FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (a)-[:HAS_CORPUS_PRIOR]->(cp)
                    )
                    
                    // Link to category if exists
                    WITH cp, p
                    OPTIONAL MATCH (cat:Category {name: p.category})
                    FOREACH (_ IN CASE WHEN cat IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (cp)-[:APPLIES_TO_CATEGORY]->(cat)
                    )
                    
                    RETURN count(cp) AS stored
                    """
                    
                    prior_dicts = []
                    for p in batch:
                        import json
                        prior_dicts.append({
                            "category": p.get("category", ""),
                            "archetype": p.get("archetype", ""),
                            "mechanism_priors_json": json.dumps(p.get("mechanism_priors", {})),
                            "confidence": p.get("confidence", 0.0),
                            "total_evidence": p.get("total_evidence", 0),
                            "transfer_sources": p.get("transfer_sources", []),
                        })
                    
                    result = await session.run(query, priors=prior_dicts)
                    record = await result.single()
                    stored += record["stored"] if record else 0
                
                logger.info(f"Stored {stored} corpus priors in Neo4j")
                return stored
        except Exception as e:
            logger.error(f"Failed to store corpus priors: {e}")
            return 0
    
    # =========================================================================
    # CORPUS FUSION: STORE PLATFORM CALIBRATIONS
    # =========================================================================
    
    async def store_platform_calibrations(
        self,
        calibrations: List[Dict[str, Any]],
    ) -> int:
        """
        Store platform-specific calibration factors as Neo4j nodes.
        
        Args:
            calibrations: List of dicts with keys:
                platform, mechanism, category, platform_factor,
                campaign_observations, convergence
        
        Returns:
            Number of calibrations stored
        """
        if not calibrations:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                stored = 0
                
                query = """
                UNWIND $cals AS c
                MERGE (pc:PlatformCalibration {
                    platform: c.platform,
                    mechanism: c.mechanism,
                    category: c.category
                })
                SET pc.platform_factor = c.platform_factor,
                    pc.campaign_observations = c.campaign_observations,
                    pc.convergence = c.convergence,
                    pc.updated_at = datetime()
                
                // Link to mechanism if exists
                WITH pc, c
                OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: c.mechanism})
                FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (pc)-[:CALIBRATES]->(m)
                )
                
                RETURN count(pc) AS stored
                """
                
                result = await session.run(query, cals=calibrations)
                record = await result.single()
                stored = record["stored"] if record else 0
                
                logger.info(f"Stored {stored} platform calibrations in Neo4j")
                return stored
        except Exception as e:
            logger.error(f"Failed to store platform calibrations: {e}")
            return 0
    
    # =========================================================================
    # CORPUS FUSION: STORE RESONANCE TEMPLATES
    # =========================================================================
    
    async def store_resonance_templates(
        self,
        templates: List[Dict[str, Any]],
    ) -> int:
        """
        Store helpful-vote-validated resonance templates as Neo4j nodes.
        
        Args:
            templates: List of dicts with keys:
                template_id, category, archetype, mechanism, pattern,
                helpful_votes, normalized_vote_score, purchase_confirmation_rate
        
        Returns:
            Number of templates stored
        """
        if not templates:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                stored = 0
                batch_size = 100
                
                for i in range(0, len(templates), batch_size):
                    batch = templates[i:i + batch_size]
                    
                    query = """
                    UNWIND $templates AS t
                    MERGE (rt:ResonanceTemplate {template_id: t.template_id})
                    SET rt.category = t.category,
                        rt.archetype = t.archetype,
                        rt.mechanism = t.mechanism,
                        rt.pattern = t.pattern,
                        rt.helpful_votes = t.helpful_votes,
                        rt.normalized_vote_score = t.normalized_vote_score,
                        rt.purchase_confirmation_rate = t.purchase_confirmation_rate,
                        rt.source = 'helpful_vote_corpus',
                        rt.updated_at = datetime()
                    
                    // Link to archetype
                    WITH rt, t
                    OPTIONAL MATCH (a:Archetype {name: t.archetype})
                    FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (a)-[:HAS_RESONANCE]->(rt)
                    )
                    
                    // Link to mechanism
                    WITH rt, t
                    OPTIONAL MATCH (m:CognitiveMechanism {mechanism_id: t.mechanism})
                    FOREACH (_ IN CASE WHEN m IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (rt)-[:USES_MECHANISM]->(m)
                    )
                    
                    RETURN count(rt) AS stored
                    """
                    
                    result = await session.run(query, templates=batch)
                    record = await result.single()
                    stored += record["stored"] if record else 0
                
                logger.info(f"Stored {stored} resonance templates in Neo4j")
                return stored
        except Exception as e:
            logger.error(f"Failed to store resonance templates: {e}")
            return 0
    
    # =========================================================================
    # CORPUS FUSION: TRAIT–CATEGORY BRIDGE (Graph Traversal)
    # =========================================================================
    
    async def store_trait_category_bridges(
        self,
        bridges: Dict[str, List[str]],
    ) -> int:
        """
        Store trait-to-category transfer bridges as graph edges.
        
        Replaces static TRAIT_CATEGORY_BRIDGES dict with traversable graph.
        
        Args:
            bridges: Dict mapping trait name → list of category names
        
        Returns:
            Number of bridge edges stored
        """
        if not bridges:
            return 0
        
        await self.initialize_schema()
        
        try:
            client = await self._get_client()
            async with await client.session() as session:
                stored = 0
                
                for trait, categories in bridges.items():
                    for cat in categories:
                        query = """
                        MERGE (t:TraitCategoryBridge {trait: $trait, category: $category})
                        SET t.updated_at = datetime()
                        
                        // Also create relationship between trait and category nodes if they exist
                        WITH t
                        OPTIONAL MATCH (trait_node:PersonalityTrait {name: $trait})
                        OPTIONAL MATCH (cat_node:Category {name: $category})
                        FOREACH (_ IN CASE WHEN trait_node IS NOT NULL AND cat_node IS NOT NULL THEN [1] ELSE [] END |
                            MERGE (trait_node)-[:TRANSFERS_TO]->(cat_node)
                        )
                        
                        RETURN count(t) AS stored
                        """
                        
                        result = await session.run(query, trait=trait, category=cat)
                        record = await result.single()
                        stored += record["stored"] if record else 0
                
                logger.info(f"Stored {stored} trait-category bridge edges in Neo4j")
                return stored
        except Exception as e:
            logger.error(f"Failed to store trait-category bridges: {e}")
            return 0
    
    async def find_transfer_categories(
        self,
        trait_profile: Dict[str, float],
        top_k: int = 5,
    ) -> List[str]:
        """
        Find transfer categories for a trait profile via graph traversal.
        
        Instead of the static TRAIT_CATEGORY_BRIDGES dict, walks the graph:
        Trait → TRANSFERS_TO → Category, weighted by trait score.
        
        Falls back to static dict if graph is unavailable.
        
        Args:
            trait_profile: Dict of {trait_name: score}
            top_k: Max categories to return
        
        Returns:
            List of category names, ranked by relevance
        """
        try:
            client = await self._get_client()
            async with await client.session() as session:
                # Get dominant traits (score > 0.5)
                dominant = [t for t, s in trait_profile.items() if s > 0.5]
                if not dominant:
                    dominant = sorted(trait_profile, key=trait_profile.get, reverse=True)[:3]
                
                query = """
                UNWIND $traits AS trait_name
                MATCH (tb:TraitCategoryBridge {trait: trait_name})
                RETURN tb.category AS category, count(*) AS relevance
                ORDER BY relevance DESC
                LIMIT $top_k
                """
                
                result = await session.run(query, traits=dominant, top_k=top_k)
                records = [record async for record in result]
                
                if records:
                    categories = [r["category"] for r in records]
                    logger.debug(f"Graph transfer categories: {categories}")
                    return categories
                
                # Fallback: try relationship-based traversal
                query2 = """
                UNWIND $traits AS trait_name
                MATCH (t:PersonalityTrait {name: trait_name})-[:TRANSFERS_TO]->(c:Category)
                RETURN c.name AS category, count(*) AS relevance
                ORDER BY relevance DESC
                LIMIT $top_k
                """
                
                result2 = await session.run(query2, traits=dominant, top_k=top_k)
                records2 = [record async for record in result2]
                
                if records2:
                    return [r["category"] for r in records2]
                
        except Exception as e:
            logger.debug(f"Graph transfer lookup failed, using static: {e}")
        
        # Final fallback: static dict
        return []


# =============================================================================
# SINGLETON
# =============================================================================

_persistence: Optional[GraphPatternPersistence] = None


def get_pattern_persistence() -> GraphPatternPersistence:
    """Get singleton pattern persistence service."""
    global _persistence
    if _persistence is None:
        _persistence = GraphPatternPersistence()
    return _persistence
