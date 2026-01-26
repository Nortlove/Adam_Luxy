# =============================================================================
# ADAM Enhancement #19: Neo4j Identity Graph
# Location: adam/identity/graph/neo4j_graph.py
# =============================================================================

"""
Neo4j-backed Identity Graph for cross-platform identity resolution.

Schema:
- UnifiedIdentity: Core identity node
- Identifier: Individual identifier nodes
- Household: Household grouping nodes
- BELONGS_TO: Identifier → UnifiedIdentity
- LINKED_TO: Identifier → Identifier (same person)
- MEMBER_OF: UnifiedIdentity → Household
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from adam.identity.models.identifiers import (
    Identifier, IdentifierType, IdentityLink, MatchConfidence
)
from adam.identity.models.identity import UnifiedIdentity
from adam.identity.models.household import Household, HouseholdMember

logger = logging.getLogger(__name__)


# =============================================================================
# NEO4J SCHEMA
# =============================================================================

IDENTITY_GRAPH_SCHEMA = """
// Constraints
CREATE CONSTRAINT identity_id_unique IF NOT EXISTS
FOR (i:UnifiedIdentity) REQUIRE i.identity_id IS UNIQUE;

CREATE CONSTRAINT identifier_id_unique IF NOT EXISTS
FOR (id:Identifier) REQUIRE id.identifier_id IS UNIQUE;

CREATE CONSTRAINT household_id_unique IF NOT EXISTS
FOR (h:Household) REQUIRE h.household_id IS UNIQUE;

// Indexes for lookup
CREATE INDEX identifier_value IF NOT EXISTS
FOR (id:Identifier) ON (id.identifier_type, id.identifier_value);

CREATE INDEX identifier_type IF NOT EXISTS
FOR (id:Identifier) ON (id.identifier_type);

CREATE INDEX identity_primary IF NOT EXISTS
FOR (i:UnifiedIdentity) ON (i.primary_identifier_type, i.primary_identifier_value);

// Full-text search for flexible matching
CREATE FULLTEXT INDEX identifier_search IF NOT EXISTS
FOR (id:Identifier) ON EACH [id.identifier_value];
"""


class IdentityGraphQueries:
    """Cypher queries for identity graph operations."""
    
    # Identity CRUD
    CREATE_IDENTITY = """
    CREATE (i:UnifiedIdentity {
        identity_id: $identity_id,
        primary_identifier_type: $primary_type,
        primary_identifier_value: $primary_value,
        total_identifiers: $total_identifiers,
        known_devices: $known_devices,
        active_devices: $active_devices,
        overall_confidence: $overall_confidence,
        linking_consent: $linking_consent,
        cross_device_consent: $cross_device_consent,
        created_at: datetime(),
        last_updated: datetime()
    })
    RETURN i
    """
    
    GET_IDENTITY = """
    MATCH (i:UnifiedIdentity {identity_id: $identity_id})
    OPTIONAL MATCH (i)<-[:BELONGS_TO]-(id:Identifier)
    RETURN i, collect(id) as identifiers
    """
    
    UPDATE_IDENTITY = """
    MATCH (i:UnifiedIdentity {identity_id: $identity_id})
    SET i.total_identifiers = $total_identifiers,
        i.known_devices = $known_devices,
        i.active_devices = $active_devices,
        i.overall_confidence = $overall_confidence,
        i.last_updated = datetime()
    RETURN i
    """
    
    # Identifier CRUD
    CREATE_IDENTIFIER = """
    CREATE (id:Identifier {
        identifier_id: $identifier_id,
        identifier_type: $identifier_type,
        identifier_value: $identifier_value,
        source: $source,
        source_system: $source_system,
        confidence: $confidence,
        verified: $verified,
        first_seen: datetime(),
        last_seen: datetime(),
        observation_count: 1
    })
    RETURN id
    """
    
    FIND_IDENTIFIER = """
    MATCH (id:Identifier {
        identifier_type: $identifier_type,
        identifier_value: $identifier_value
    })
    RETURN id
    """
    
    LINK_IDENTIFIER_TO_IDENTITY = """
    MATCH (i:UnifiedIdentity {identity_id: $identity_id})
    MATCH (id:Identifier {identifier_id: $identifier_id})
    MERGE (id)-[r:BELONGS_TO]->(i)
    SET r.linked_at = datetime(),
        r.confidence = $confidence
    RETURN r
    """
    
    # Identity Resolution
    FIND_IDENTITY_BY_IDENTIFIER = """
    MATCH (id:Identifier {
        identifier_type: $identifier_type,
        identifier_value: $identifier_value
    })-[:BELONGS_TO]->(i:UnifiedIdentity)
    RETURN i, id
    """
    
    FIND_IDENTITIES_BY_IP = """
    MATCH (id:Identifier {
        identifier_type: 'ip_hash',
        identifier_value: $ip_hash
    })-[:BELONGS_TO]->(i:UnifiedIdentity)
    RETURN DISTINCT i
    LIMIT 100
    """
    
    # Link creation
    CREATE_IDENTITY_LINK = """
    MATCH (source:Identifier {identifier_id: $source_id})
    MATCH (target:Identifier {identifier_id: $target_id})
    MERGE (source)-[r:LINKED_TO]->(target)
    SET r.link_id = $link_id,
        r.match_type = $match_type,
        r.confidence = $confidence,
        r.confidence_score = $confidence_score,
        r.match_algorithm = $match_algorithm,
        r.created_at = datetime()
    RETURN r
    """
    
    # Merge identities
    MERGE_IDENTITIES = """
    MATCH (primary:UnifiedIdentity {identity_id: $primary_id})
    MATCH (secondary:UnifiedIdentity {identity_id: $secondary_id})
    MATCH (secondary)<-[:BELONGS_TO]-(id:Identifier)
    
    // Move all identifiers to primary
    MERGE (id)-[:BELONGS_TO]->(primary)
    
    // Update primary counts
    SET primary.total_identifiers = primary.total_identifiers + secondary.total_identifiers,
        primary.known_devices = primary.known_devices + secondary.known_devices,
        primary.last_updated = datetime()
    
    // Record merge
    SET primary.merge_history = coalesce(primary.merge_history, []) + [$secondary_id]
    
    // Delete secondary
    DETACH DELETE secondary
    
    RETURN primary
    """
    
    # Household operations
    CREATE_HOUSEHOLD = """
    CREATE (h:Household {
        household_id: $household_id,
        estimated_size: $estimated_size,
        overall_confidence: $overall_confidence,
        created_at: datetime()
    })
    RETURN h
    """
    
    ADD_TO_HOUSEHOLD = """
    MATCH (i:UnifiedIdentity {identity_id: $identity_id})
    MATCH (h:Household {household_id: $household_id})
    MERGE (i)-[r:MEMBER_OF]->(h)
    SET r.role = $role,
        r.confidence = $confidence,
        r.joined_at = datetime()
    SET i.household_id = $household_id,
        i.household_role = $role
    RETURN r
    """


class Neo4jIdentityGraph:
    """
    Neo4j-backed identity graph.
    
    Provides CRUD operations for:
    - Unified identities
    - Individual identifiers
    - Identity links
    - Household membership
    """
    
    def __init__(self, neo4j_driver=None):
        self.driver = neo4j_driver
        self.queries = IdentityGraphQueries()
        
        # Statistics
        self._identities_created = 0
        self._identifiers_created = 0
        self._links_created = 0
    
    async def initialize_schema(self) -> bool:
        """Initialize graph schema with constraints and indexes."""
        if not self.driver:
            logger.warning("No Neo4j driver - schema not initialized")
            return False
        
        try:
            async with self.driver.session() as session:
                for statement in IDENTITY_GRAPH_SCHEMA.split(";"):
                    if statement.strip():
                        await session.run(statement)
            logger.info("Identity graph schema initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            return False
    
    async def create_identity(
        self,
        identity: UnifiedIdentity
    ) -> Optional[UnifiedIdentity]:
        """Create a new unified identity."""
        if not self.driver:
            self._identities_created += 1
            return identity
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    self.queries.CREATE_IDENTITY,
                    identity_id=identity.identity_id,
                    primary_type=identity.primary_identifier_type.value if identity.primary_identifier_type else None,
                    primary_value=identity.primary_identifier_value,
                    total_identifiers=identity.total_identifiers,
                    known_devices=identity.known_devices,
                    active_devices=identity.active_devices,
                    overall_confidence=identity.overall_confidence,
                    linking_consent=identity.linking_consent,
                    cross_device_consent=identity.cross_device_consent,
                )
                record = await result.single()
                
                self._identities_created += 1
                return identity
                
        except Exception as e:
            logger.error(f"Failed to create identity: {e}")
            return None
    
    async def get_identity(
        self,
        identity_id: str
    ) -> Optional[UnifiedIdentity]:
        """Get identity by ID."""
        if not self.driver:
            return None
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    self.queries.GET_IDENTITY,
                    identity_id=identity_id
                )
                record = await result.single()
                
                if not record:
                    return None
                
                # Convert Neo4j node to model
                node = record["i"]
                return self._node_to_identity(node)
                
        except Exception as e:
            logger.error(f"Failed to get identity: {e}")
            return None
    
    async def find_identity_by_identifier(
        self,
        identifier_type: IdentifierType,
        identifier_value: str
    ) -> Optional[UnifiedIdentity]:
        """Find identity by identifier value."""
        if not self.driver:
            return None
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    self.queries.FIND_IDENTITY_BY_IDENTIFIER,
                    identifier_type=identifier_type.value,
                    identifier_value=identifier_value
                )
                record = await result.single()
                
                if not record:
                    return None
                
                return self._node_to_identity(record["i"])
                
        except Exception as e:
            logger.error(f"Failed to find identity: {e}")
            return None
    
    async def create_identifier(
        self,
        identifier: Identifier,
        identity_id: Optional[str] = None
    ) -> bool:
        """Create identifier, optionally linking to identity."""
        if not self.driver:
            self._identifiers_created += 1
            return True
        
        try:
            async with self.driver.session() as session:
                # Create identifier
                await session.run(
                    self.queries.CREATE_IDENTIFIER,
                    identifier_id=identifier.identifier_id,
                    identifier_type=identifier.identifier_type.value,
                    identifier_value=identifier.identifier_value,
                    source=identifier.source.value,
                    source_system=identifier.source_system,
                    confidence=identifier.confidence,
                    verified=identifier.verified,
                )
                
                # Link to identity if provided
                if identity_id:
                    await session.run(
                        self.queries.LINK_IDENTIFIER_TO_IDENTITY,
                        identity_id=identity_id,
                        identifier_id=identifier.identifier_id,
                        confidence=identifier.confidence,
                    )
                
                self._identifiers_created += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to create identifier: {e}")
            return False
    
    async def create_link(
        self,
        link: IdentityLink
    ) -> bool:
        """Create link between identifiers."""
        if not self.driver:
            self._links_created += 1
            return True
        
        try:
            async with self.driver.session() as session:
                await session.run(
                    self.queries.CREATE_IDENTITY_LINK,
                    link_id=link.link_id,
                    source_id=link.source_identifier_id,
                    target_id=link.target_identifier_id,
                    match_type=link.match_type,
                    confidence=link.confidence.value,
                    confidence_score=link.confidence_score,
                    match_algorithm=link.match_algorithm,
                )
                
                self._links_created += 1
                return True
                
        except Exception as e:
            logger.error(f"Failed to create link: {e}")
            return False
    
    async def merge_identities(
        self,
        primary_id: str,
        secondary_id: str
    ) -> Optional[UnifiedIdentity]:
        """Merge two identities."""
        if not self.driver:
            return None
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    self.queries.MERGE_IDENTITIES,
                    primary_id=primary_id,
                    secondary_id=secondary_id,
                )
                record = await result.single()
                
                if record:
                    return self._node_to_identity(record["primary"])
                return None
                
        except Exception as e:
            logger.error(f"Failed to merge identities: {e}")
            return None
    
    async def add_to_household(
        self,
        identity_id: str,
        household_id: str,
        role: str = "unknown",
        confidence: float = 0.6
    ) -> bool:
        """Add identity to household."""
        if not self.driver:
            return True
        
        try:
            async with self.driver.session() as session:
                # Ensure household exists
                await session.run(
                    self.queries.CREATE_HOUSEHOLD,
                    household_id=household_id,
                    estimated_size=1,
                    overall_confidence=confidence,
                )
                
                # Add member
                await session.run(
                    self.queries.ADD_TO_HOUSEHOLD,
                    identity_id=identity_id,
                    household_id=household_id,
                    role=role,
                    confidence=confidence,
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to add to household: {e}")
            return False
    
    def _node_to_identity(self, node) -> UnifiedIdentity:
        """Convert Neo4j node to UnifiedIdentity."""
        return UnifiedIdentity(
            identity_id=node["identity_id"],
            primary_identifier_type=IdentifierType(node["primary_identifier_type"]) if node.get("primary_identifier_type") else None,
            primary_identifier_value=node.get("primary_identifier_value"),
            total_identifiers=node.get("total_identifiers", 0),
            known_devices=node.get("known_devices", 0),
            active_devices=node.get("active_devices", 0),
            overall_confidence=node.get("overall_confidence", 0.5),
            household_id=node.get("household_id"),
            household_role=node.get("household_role"),
        )
    
    def get_statistics(self) -> Dict[str, int]:
        """Get graph statistics."""
        return {
            "identities_created": self._identities_created,
            "identifiers_created": self._identifiers_created,
            "links_created": self._links_created,
        }


# Singleton instance
_graph: Optional[Neo4jIdentityGraph] = None


def get_identity_graph(neo4j_driver=None) -> Neo4jIdentityGraph:
    """Get singleton identity graph."""
    global _graph
    if _graph is None:
        _graph = Neo4jIdentityGraph(neo4j_driver)
    return _graph
