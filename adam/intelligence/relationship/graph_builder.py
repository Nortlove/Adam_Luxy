"""
Relationship Graph Builder
==========================

Neo4j integration for the Consumer-Brand Relationship Detection System.

This module handles:
1. Storing detected relationships and signals in Neo4j
2. Querying relationships by brand, consumer, or type
3. Tracking relationship evolution over time
4. Supporting learning by storing outcomes linked to relationships
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from neo4j import AsyncSession

from .models import (
    ObservationChannel,
    RelationshipTypeId,
    RelationshipSignal,
    ConsumerBrandRelationship,
)


logger = logging.getLogger(__name__)


# =============================================================================
# CYPHER QUERIES
# =============================================================================

# Create/Update Relationship Profile
CREATE_RELATIONSHIP = """
MERGE (r:ConsumerBrandRelationship {relationship_id: $relationship_id})
SET r += $properties,
    r.updated_at = datetime()
WITH r

// Link to brand
MERGE (b:Brand {brand_id: $brand_id})
MERGE (r)-[:FOR_BRAND]->(b)

// Link to relationship type
MERGE (rt:RelationshipType {type_id: $relationship_type})
MERGE (r)-[:IS_TYPE {confidence: $confidence}]->(rt)

RETURN r.relationship_id as id
"""

# Create Signal
CREATE_SIGNAL = """
MERGE (s:RelationshipSignal {signal_id: $signal_id})
SET s += $properties,
    s.created_at = datetime()
WITH s

// Link to channel
MERGE (ch:ObservationChannel {channel_id: $channel})
MERGE (s)-[:FROM_CHANNEL]->(ch)

// Link to relationship type
MERGE (rt:RelationshipType {type_id: $relationship_type})
MERGE (s)-[:INDICATES {confidence: $confidence}]->(rt)

// Link to brand if provided
FOREACH (bid IN CASE WHEN $brand_id IS NOT NULL THEN [$brand_id] ELSE [] END |
    MERGE (b:Brand {brand_id: bid})
    MERGE (s)-[:ABOUT_BRAND]->(b)
)

// Link matched patterns
FOREACH (pattern_id IN $patterns |
    MERGE (lp:LanguagePattern {pattern_id: pattern_id})
    MERGE (s)-[:MATCHED]->(lp)
)

RETURN s.signal_id as id
"""

# Link Signal to Relationship
LINK_SIGNAL_TO_RELATIONSHIP = """
MATCH (s:RelationshipSignal {signal_id: $signal_id})
MATCH (r:ConsumerBrandRelationship {relationship_id: $relationship_id})
MERGE (r)-[:HAS_SIGNAL]->(s)
"""

# Query Relationship by Brand
QUERY_BRAND_RELATIONSHIPS = """
MATCH (r:ConsumerBrandRelationship)-[:FOR_BRAND]->(b:Brand {brand_id: $brand_id})
MATCH (r)-[it:IS_TYPE]->(rt:RelationshipType)
OPTIONAL MATCH (r)-[:HAS_SIGNAL]->(s:RelationshipSignal)
WITH r, rt, it.confidence as confidence, collect(s.signal_id) as signals
ORDER BY confidence DESC
RETURN r {
    .relationship_id,
    .primary_relationship_type,
    .primary_confidence,
    .strength,
    .strength_score,
    .emotional_intensity,
    .identity_integration,
    .social_function,
    .recommended_engagement_strategy,
    relationship_type: rt.type_id,
    confidence: confidence,
    signal_ids: signals
} as relationship
LIMIT $limit
"""

# Query Relationship Distribution for Brand
QUERY_BRAND_RELATIONSHIP_DISTRIBUTION = """
MATCH (r:ConsumerBrandRelationship)-[:FOR_BRAND]->(b:Brand {brand_id: $brand_id})
MATCH (r)-[it:IS_TYPE]->(rt:RelationshipType)
WITH rt.type_id as relationship_type, 
     avg(r.primary_confidence) as avg_confidence,
     count(r) as count,
     avg(r.strength_score) as avg_strength
RETURN relationship_type, avg_confidence, count, avg_strength
ORDER BY count DESC
"""

# Get Most Common Relationship Type for Brand
QUERY_PRIMARY_RELATIONSHIP_TYPE = """
MATCH (r:ConsumerBrandRelationship)-[:FOR_BRAND]->(b:Brand {brand_id: $brand_id})
WITH r.primary_relationship_type as rel_type, count(*) as count
ORDER BY count DESC
LIMIT 1
RETURN rel_type, count
"""

# Query Signals by Channel
QUERY_SIGNALS_BY_CHANNEL = """
MATCH (s:RelationshipSignal)-[:FROM_CHANNEL]->(ch:ObservationChannel {channel_id: $channel})
WHERE s.brand_id = $brand_id
OPTIONAL MATCH (s)-[ind:INDICATES]->(rt:RelationshipType)
RETURN s {
    .signal_id,
    .source_text,
    .confidence,
    .emotional_intensity,
    .identity_integration,
    .social_display,
    relationship_type: rt.type_id,
    indicate_confidence: ind.confidence
}
ORDER BY s.confidence DESC
LIMIT $limit
"""

# Track Relationship Outcome (for learning)
RECORD_RELATIONSHIP_OUTCOME = """
MATCH (r:ConsumerBrandRelationship {relationship_id: $relationship_id})
CREATE (o:RelationshipOutcome {
    outcome_id: $outcome_id,
    ad_id: $ad_id,
    success: $success,
    engagement_score: $engagement_score,
    conversion: $conversion,
    timestamp: datetime()
})
MERGE (r)-[:HAD_OUTCOME]->(o)

// Link to mechanism used
FOREACH (mech IN CASE WHEN $mechanism IS NOT NULL THEN [$mechanism] ELSE [] END |
    MERGE (m:PsychologicalMechanism {mechanism_id: mech})
    MERGE (o)-[:USED_MECHANISM]->(m)
)

RETURN o.outcome_id as id
"""

# Update Relationship-Mechanism Effectiveness
UPDATE_RELATIONSHIP_MECHANISM_EFFECTIVENESS = """
MATCH (rt:RelationshipType {type_id: $relationship_type})
MATCH (m:PsychologicalMechanism {mechanism_id: $mechanism_id})
MERGE (rt)-[eff:MECHANISM_EFFECTIVENESS]->(m)
ON CREATE SET 
    eff.total_trials = 1,
    eff.successes = CASE WHEN $success THEN 1 ELSE 0 END,
    eff.effectiveness = CASE WHEN $success THEN 1.0 ELSE 0.0 END
ON MATCH SET
    eff.total_trials = eff.total_trials + 1,
    eff.successes = eff.successes + CASE WHEN $success THEN 1 ELSE 0 END,
    eff.effectiveness = toFloat(eff.successes + CASE WHEN $success THEN 1 ELSE 0 END) / toFloat(eff.total_trials + 1)
RETURN eff.effectiveness as effectiveness
"""

# Query Mechanism Effectiveness for Relationship Type
QUERY_MECHANISM_EFFECTIVENESS = """
MATCH (rt:RelationshipType {type_id: $relationship_type})
         -[eff:MECHANISM_EFFECTIVENESS]->(m:PsychologicalMechanism)
WHERE eff.total_trials >= $min_trials
RETURN m.mechanism_id as mechanism,
       eff.effectiveness as effectiveness,
       eff.total_trials as trials
ORDER BY eff.effectiveness DESC
LIMIT $limit
"""

# Get Engagement Strategy Performance
QUERY_STRATEGY_PERFORMANCE = """
MATCH (r:ConsumerBrandRelationship)-[:HAD_OUTCOME]->(o:RelationshipOutcome)
WHERE r.recommended_engagement_strategy = $strategy
WITH r.primary_relationship_type as rel_type,
     avg(o.engagement_score) as avg_engagement,
     sum(CASE WHEN o.conversion THEN 1 ELSE 0 END) as conversions,
     count(o) as total
RETURN rel_type, avg_engagement, conversions, total,
       toFloat(conversions) / toFloat(total) as conversion_rate
ORDER BY conversion_rate DESC
"""


class RelationshipGraphBuilder:
    """
    Manages storing and querying consumer-brand relationships in Neo4j.
    """
    
    def __init__(self, neo4j_driver):
        """
        Initialize the graph builder.
        
        Args:
            neo4j_driver: Neo4j async driver instance
        """
        self.driver = neo4j_driver
    
    async def store_relationship(
        self,
        relationship: ConsumerBrandRelationship,
        signals: Optional[List[RelationshipSignal]] = None
    ) -> str:
        """
        Store a detected consumer-brand relationship in Neo4j.
        
        Args:
            relationship: The relationship profile to store
            signals: Optional list of signals that contributed to this relationship
            
        Returns:
            The relationship_id
        """
        async with self.driver.session() as session:
            # Store the relationship
            result = await session.run(
                CREATE_RELATIONSHIP,
                relationship_id=relationship.relationship_id,
                brand_id=relationship.brand_id,
                relationship_type=relationship.primary_relationship_type.value,
                confidence=relationship.primary_confidence,
                properties=relationship.to_neo4j_properties(),
            )
            record = await result.single()
            rel_id = record['id'] if record else relationship.relationship_id
            
            # Store and link signals if provided
            if signals:
                for signal in signals:
                    await self._store_signal(session, signal)
                    await session.run(
                        LINK_SIGNAL_TO_RELATIONSHIP,
                        signal_id=signal.signal_id,
                        relationship_id=rel_id,
                    )
            
            logger.info(f"Stored relationship {rel_id} for brand {relationship.brand_id}")
            return rel_id
    
    async def _store_signal(
        self,
        session: AsyncSession,
        signal: RelationshipSignal
    ) -> str:
        """Store a single signal in Neo4j."""
        result = await session.run(
            CREATE_SIGNAL,
            signal_id=signal.signal_id,
            channel=signal.channel.value,
            relationship_type=signal.relationship_type.value,
            confidence=signal.confidence,
            brand_id=signal.brand_id,
            patterns=signal.matched_patterns,
            properties=signal.to_neo4j_properties(),
        )
        record = await result.single()
        return record['id'] if record else signal.signal_id
    
    async def get_brand_relationships(
        self,
        brand_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all detected relationships for a brand.
        
        Args:
            brand_id: The brand identifier
            limit: Maximum number of relationships to return
            
        Returns:
            List of relationship data dictionaries
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRAND_RELATIONSHIPS,
                brand_id=brand_id,
                limit=limit,
            )
            records = await result.data()
            return [r['relationship'] for r in records]
    
    async def get_brand_relationship_distribution(
        self,
        brand_id: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Get distribution of relationship types for a brand.
        
        Returns dict like:
        {
            "committed_partnership": {"count": 45, "avg_confidence": 0.82, "avg_strength": 0.75},
            "reliable_tool": {"count": 30, "avg_confidence": 0.70, "avg_strength": 0.55},
            ...
        }
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_BRAND_RELATIONSHIP_DISTRIBUTION,
                brand_id=brand_id,
            )
            records = await result.data()
            
            distribution = {}
            for r in records:
                distribution[r['relationship_type']] = {
                    'count': r['count'],
                    'avg_confidence': r['avg_confidence'],
                    'avg_strength': r['avg_strength'],
                }
            return distribution
    
    async def get_primary_relationship_type(
        self,
        brand_id: str
    ) -> Optional[Tuple[str, int]]:
        """
        Get the most common relationship type for a brand.
        
        Returns:
            Tuple of (relationship_type, count) or None
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_PRIMARY_RELATIONSHIP_TYPE,
                brand_id=brand_id,
            )
            record = await result.single()
            if record:
                return (record['rel_type'], record['count'])
            return None
    
    async def get_signals_by_channel(
        self,
        brand_id: str,
        channel: ObservationChannel,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get signals for a brand from a specific channel."""
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_SIGNALS_BY_CHANNEL,
                brand_id=brand_id,
                channel=channel.value,
                limit=limit,
            )
            return await result.data()
    
    async def record_outcome(
        self,
        relationship_id: str,
        ad_id: str,
        success: bool,
        engagement_score: float = 0.0,
        conversion: bool = False,
        mechanism: Optional[str] = None,
    ) -> str:
        """
        Record an ad outcome for a relationship (for learning).
        
        Args:
            relationship_id: The relationship that was targeted
            ad_id: The ad that was shown
            success: Whether the ad was successful (engagement threshold met)
            engagement_score: Numeric engagement score
            conversion: Whether a conversion occurred
            mechanism: The psychological mechanism used
            
        Returns:
            The outcome_id
        """
        import uuid
        outcome_id = f"out_{uuid.uuid4().hex[:12]}"
        
        async with self.driver.session() as session:
            result = await session.run(
                RECORD_RELATIONSHIP_OUTCOME,
                relationship_id=relationship_id,
                outcome_id=outcome_id,
                ad_id=ad_id,
                success=success,
                engagement_score=engagement_score,
                conversion=conversion,
                mechanism=mechanism,
            )
            record = await result.single()
            
            # Update mechanism effectiveness if mechanism was specified
            if mechanism:
                # Get the relationship type
                rel_result = await session.run(
                    "MATCH (r:ConsumerBrandRelationship {relationship_id: $rid}) "
                    "RETURN r.primary_relationship_type as rel_type",
                    rid=relationship_id,
                )
                rel_record = await rel_result.single()
                if rel_record:
                    await session.run(
                        UPDATE_RELATIONSHIP_MECHANISM_EFFECTIVENESS,
                        relationship_type=rel_record['rel_type'],
                        mechanism_id=mechanism,
                        success=success,
                    )
            
            return record['id'] if record else outcome_id
    
    async def get_mechanism_effectiveness(
        self,
        relationship_type: RelationshipTypeId,
        min_trials: int = 5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get mechanism effectiveness for a relationship type (learned from outcomes).
        
        Returns list of {mechanism, effectiveness, trials}
        """
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_MECHANISM_EFFECTIVENESS,
                relationship_type=relationship_type.value,
                min_trials=min_trials,
                limit=limit,
            )
            return await result.data()
    
    async def get_strategy_performance(
        self,
        strategy: str
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for an engagement strategy."""
        async with self.driver.session() as session:
            result = await session.run(
                QUERY_STRATEGY_PERFORMANCE,
                strategy=strategy,
            )
            return await result.data()


# Cypher schema initialization queries
SCHEMA_QUERIES = [
    # Constraints
    "CREATE CONSTRAINT relationship_id IF NOT EXISTS FOR (r:ConsumerBrandRelationship) REQUIRE r.relationship_id IS UNIQUE",
    "CREATE CONSTRAINT signal_id IF NOT EXISTS FOR (s:RelationshipSignal) REQUIRE s.signal_id IS UNIQUE",
    "CREATE CONSTRAINT channel_id IF NOT EXISTS FOR (ch:ObservationChannel) REQUIRE ch.channel_id IS UNIQUE",
    "CREATE CONSTRAINT pattern_id IF NOT EXISTS FOR (lp:LanguagePattern) REQUIRE lp.pattern_id IS UNIQUE",
    
    # Indexes
    "CREATE INDEX rel_brand IF NOT EXISTS FOR (r:ConsumerBrandRelationship) ON (r.brand_id)",
    "CREATE INDEX rel_type IF NOT EXISTS FOR (r:ConsumerBrandRelationship) ON (r.primary_relationship_type)",
    "CREATE INDEX signal_channel IF NOT EXISTS FOR (s:RelationshipSignal) ON (s.channel)",
    "CREATE INDEX signal_brand IF NOT EXISTS FOR (s:RelationshipSignal) ON (s.brand_id)",
]


async def initialize_relationship_schema(driver) -> None:
    """Initialize the Neo4j schema for relationship storage."""
    async with driver.session() as session:
        for query in SCHEMA_QUERIES:
            try:
                await session.run(query)
            except Exception as e:
                logger.warning(f"Schema query warning (may already exist): {e}")
        
        logger.info("Relationship graph schema initialized")
