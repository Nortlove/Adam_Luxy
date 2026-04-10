#!/usr/bin/env python3
"""
GRAPH MAINTENANCE & INTELLIGENCE ACTIVATION
===========================================

Activates Neo4j Graph Data Science (GDS) algorithms to extract
higher-level intelligence that individual queries cannot produce:

1. **PageRank** - Identify influential mechanisms and archetypes
2. **Community Detection (Louvain)** - Find natural user clusters
3. **Node Similarity** - Discover similar users for cold start
4. **Path Analysis** - Trace successful decision paths
5. **Emergence Detection** - Find new patterns

These algorithms should run periodically (not on every request) to:
- Update mechanism influence scores
- Refresh archetype clusters
- Detect emerging patterns
- Compute user similarity for recommendations

Phase 1: Fix Learning Loop - Activate Graph Intelligence
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# GDS QUERIES
# =============================================================================

# PageRank on mechanisms to find most influential
MECHANISM_PAGERANK_QUERY = """
// Project mechanism effectiveness graph
CALL gds.graph.project(
    'mechanism_influence',
    ['CognitiveMechanism', 'User', 'AdDecision'],
    {
        APPLIED_MECHANISM: {
            type: 'APPLIED_MECHANISM',
            orientation: 'UNDIRECTED',
            properties: ['intensity']
        },
        MADE_AD_DECISION: {
            type: 'MADE_AD_DECISION',
            orientation: 'UNDIRECTED'
        }
    }
) YIELD graphName, nodeCount, relationshipCount

// Run PageRank
CALL gds.pageRank.stream('mechanism_influence', {
    maxIterations: 20,
    dampingFactor: 0.85
})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS node, score
WHERE node:CognitiveMechanism
RETURN node.name AS mechanism, score AS influence_score
ORDER BY score DESC
LIMIT 20
"""

MECHANISM_PAGERANK_SIMPLE = """
// Simpler PageRank for mechanism influence without GDS
MATCH (m:CognitiveMechanism)<-[r:APPLIED_MECHANISM]-(d:AdDecision)
WITH m, count(r) AS usage_count, avg(r.intensity) AS avg_intensity
OPTIONAL MATCH (d:AdDecision)-[:APPLIED_MECHANISM]->(m)
WHERE (d)-[:HAD_OUTCOME]->(:AdOutcome {outcome_type: 'conversion'})
WITH m, usage_count, avg_intensity, count(d) AS success_count
RETURN 
    m.name AS mechanism,
    usage_count,
    success_count,
    CASE WHEN usage_count > 0 
        THEN toFloat(success_count) / usage_count 
        ELSE 0.5 
    END AS success_rate,
    avg_intensity,
    (usage_count * 0.3 + success_count * 0.7) AS influence_score
ORDER BY influence_score DESC
"""

# Community detection for user clustering
USER_COMMUNITY_QUERY = """
// Project user-archetype-mechanism graph
CALL gds.graph.project(
    'user_communities',
    ['User', 'Archetype', 'CognitiveMechanism'],
    ['MATCHES_ARCHETYPE', 'RESPONDS_TO', 'APPLIED_MECHANISM']
) YIELD graphName

// Run Louvain community detection
CALL gds.louvain.stream('user_communities')
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS node, communityId
WHERE node:User
RETURN node.user_id AS user_id, communityId AS community
ORDER BY communityId
"""

USER_COMMUNITY_SIMPLE = """
// Simpler community detection via archetype grouping
MATCH (u:User)-[:MATCHES_ARCHETYPE]->(a:Archetype)
WITH a.name AS archetype, collect(u.user_id) AS users, count(u) AS user_count
RETURN archetype AS community_name, users, user_count
ORDER BY user_count DESC
"""

# Node similarity for cold start
USER_SIMILARITY_QUERY = """
// Project user-mechanism interaction graph
CALL gds.graph.project(
    'user_similarity',
    ['User', 'CognitiveMechanism'],
    ['RESPONDED_TO']
) YIELD graphName

// Run node similarity
CALL gds.nodeSimilarity.stream('user_similarity', {
    topK: 10
})
YIELD node1, node2, similarity
WITH gds.util.asNode(node1) AS user1, gds.util.asNode(node2) AS user2, similarity
WHERE user1:User AND user2:User
RETURN user1.user_id AS user_a, user2.user_id AS user_b, similarity
ORDER BY similarity DESC
LIMIT 100
"""

USER_SIMILARITY_SIMPLE = """
// Simpler similarity via shared archetype and mechanisms
MATCH (u1:User)-[:MATCHES_ARCHETYPE]->(a:Archetype)<-[:MATCHES_ARCHETYPE]-(u2:User)
WHERE u1.user_id < u2.user_id  // Avoid duplicates
WITH u1, u2, count(a) AS shared_archetypes
MATCH (u1)-[:MADE_AD_DECISION]->(:AdDecision)-[:APPLIED_MECHANISM]->(m:CognitiveMechanism)
       <-[:APPLIED_MECHANISM]-(:AdDecision)<-[:MADE_AD_DECISION]-(u2)
WITH u1, u2, shared_archetypes, count(DISTINCT m) AS shared_mechanisms
RETURN 
    u1.user_id AS user_a, 
    u2.user_id AS user_b,
    shared_archetypes,
    shared_mechanisms,
    (shared_archetypes * 0.4 + shared_mechanisms * 0.6) / 10.0 AS similarity
ORDER BY similarity DESC
LIMIT 100
"""

# Successful decision path analysis
SUCCESS_PATH_QUERY = """
// Find paths that led to successful outcomes
MATCH path = (u:User)-[:MADE_AD_DECISION]->(d:AdDecision)
              -[:APPLIED_MECHANISM]->(m:CognitiveMechanism)
WHERE EXISTS((d)-[:HAD_OUTCOME]->(:AdOutcome {outcome_value: 1.0}))
WITH u, d, m, 
     [(d)-[:HAD_OUTCOME]->(o:AdOutcome) | o.outcome_value][0] AS outcome
WHERE outcome >= 0.7
MATCH (u)-[:MATCHES_ARCHETYPE]->(a:Archetype)
RETURN 
    a.name AS archetype,
    m.name AS mechanism,
    count(*) AS success_count,
    avg(outcome) AS avg_outcome
ORDER BY success_count DESC
LIMIT 50
"""

# Emergence detection - new patterns
EMERGENCE_DETECTION_QUERY = """
// Find mechanism-archetype pairs with increasing success over time
MATCH (d:AdDecision)-[:APPLIED_MECHANISM]->(m:CognitiveMechanism)
MATCH (d)-[:HAD_OUTCOME]->(o:AdOutcome)
MATCH (u:User)-[:MADE_AD_DECISION]->(d)
MATCH (u)-[:MATCHES_ARCHETYPE]->(a:Archetype)
WHERE o.observed_at > datetime() - duration('P7D')  // Last 7 days
WITH a.name AS archetype, m.name AS mechanism,
     count(*) AS recent_count,
     avg(o.outcome_value) AS recent_success_rate
// Compare to historical
MATCH (d2:AdDecision)-[:APPLIED_MECHANISM]->(m2:CognitiveMechanism {name: mechanism})
MATCH (d2)-[:HAD_OUTCOME]->(o2:AdOutcome)
WHERE o2.observed_at < datetime() - duration('P7D')
  AND o2.observed_at > datetime() - duration('P30D')  // 7-30 days ago
WITH archetype, mechanism, recent_count, recent_success_rate,
     count(*) AS historical_count,
     avg(o2.outcome_value) AS historical_success_rate
WHERE recent_success_rate > historical_success_rate + 0.1  // 10% improvement
  AND recent_count >= 5  // Minimum sample
RETURN archetype, mechanism, 
       recent_success_rate, historical_success_rate,
       recent_success_rate - historical_success_rate AS improvement,
       recent_count
ORDER BY improvement DESC
"""


# =============================================================================
# GRAPH MAINTENANCE SERVICE
# =============================================================================

@dataclass
class MaintenanceResult:
    """Result of a maintenance operation."""
    
    operation: str
    success: bool
    records_processed: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


class GraphMaintenanceService:
    """
    Service for running graph maintenance and GDS algorithms.
    
    Should be run periodically (e.g., every hour or after X decisions).
    """
    
    def __init__(self, driver=None):
        self._driver = driver
        self._last_maintenance: Optional[datetime] = None
        self._gds_available: Optional[bool] = None
    
    async def check_gds_available(self) -> bool:
        """Check if GDS library is available."""
        if self._gds_available is not None:
            return self._gds_available
        
        if not self._driver:
            self._gds_available = False
            return False
        
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN gds.version() AS version")
                record = await result.single()
                if record:
                    logger.info(f"GDS version: {record['version']}")
                    self._gds_available = True
                    return True
        except Exception as e:
            logger.info(f"GDS not available, using simple queries: {e}")
            self._gds_available = False
        
        return False
    
    async def run_full_maintenance(self) -> List[MaintenanceResult]:
        """
        Run full graph maintenance.
        
        Includes:
        1. Mechanism influence scoring
        2. User community detection
        3. User similarity computation
        4. Success path analysis
        5. Emergence detection
        """
        results = []
        
        gds = await self.check_gds_available()
        
        # 1. Mechanism influence
        results.append(await self._run_mechanism_influence(gds))
        
        # 2. User communities
        results.append(await self._run_user_communities(gds))
        
        # 3. User similarity
        results.append(await self._run_user_similarity(gds))
        
        # 4. Success paths
        results.append(await self._run_success_path_analysis())
        
        # 5. Emergence detection
        results.append(await self._run_emergence_detection())
        
        self._last_maintenance = datetime.now(timezone.utc)
        
        # Log summary
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Graph maintenance complete: {success_count}/{len(results)} operations succeeded"
        )
        
        return results
    
    async def _run_mechanism_influence(self, use_gds: bool) -> MaintenanceResult:
        """Run mechanism influence scoring."""
        start = datetime.now(timezone.utc)
        
        query = MECHANISM_PAGERANK_QUERY if use_gds else MECHANISM_PAGERANK_SIMPLE
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                # Store results back to graph
                for record in records:
                    await session.run(
                        """
                        MATCH (m:CognitiveMechanism {name: $name})
                        SET m.influence_score = $score,
                            m.influence_updated_at = datetime()
                        """,
                        name=record.get("mechanism"),
                        score=record.get("influence_score", 0),
                    )
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                return MaintenanceResult(
                    operation="mechanism_influence",
                    success=True,
                    records_processed=len(records),
                    data={"top_mechanisms": records[:5]},
                    duration_ms=duration,
                )
                
        except Exception as e:
            return MaintenanceResult(
                operation="mechanism_influence",
                success=False,
                error=str(e),
            )
    
    async def _run_user_communities(self, use_gds: bool) -> MaintenanceResult:
        """Run user community detection."""
        start = datetime.now(timezone.utc)
        
        query = USER_COMMUNITY_QUERY if use_gds else USER_COMMUNITY_SIMPLE
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                return MaintenanceResult(
                    operation="user_communities",
                    success=True,
                    records_processed=len(records),
                    data={"communities": len(records)},
                    duration_ms=duration,
                )
                
        except Exception as e:
            return MaintenanceResult(
                operation="user_communities",
                success=False,
                error=str(e),
            )
    
    async def _run_user_similarity(self, use_gds: bool) -> MaintenanceResult:
        """Run user similarity computation."""
        start = datetime.now(timezone.utc)
        
        query = USER_SIMILARITY_QUERY if use_gds else USER_SIMILARITY_SIMPLE
        
        try:
            async with self._driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                # Store similarity edges
                for record in records:
                    await session.run(
                        """
                        MATCH (u1:User {user_id: $user_a})
                        MATCH (u2:User {user_id: $user_b})
                        MERGE (u1)-[r:SIMILAR_TO]->(u2)
                        SET r.similarity = $similarity,
                            r.computed_at = datetime()
                        """,
                        user_a=record.get("user_a"),
                        user_b=record.get("user_b"),
                        similarity=record.get("similarity", 0),
                    )
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                return MaintenanceResult(
                    operation="user_similarity",
                    success=True,
                    records_processed=len(records),
                    data={"pairs_computed": len(records)},
                    duration_ms=duration,
                )
                
        except Exception as e:
            return MaintenanceResult(
                operation="user_similarity",
                success=False,
                error=str(e),
            )
    
    async def _run_success_path_analysis(self) -> MaintenanceResult:
        """Analyze successful decision paths."""
        start = datetime.now(timezone.utc)
        
        try:
            async with self._driver.session() as session:
                result = await session.run(SUCCESS_PATH_QUERY)
                records = await result.data()
                
                # Store archetype-mechanism effectiveness
                for record in records:
                    await session.run(
                        """
                        MATCH (a:Archetype {name: $archetype})
                        MATCH (m:CognitiveMechanism {name: $mechanism})
                        MERGE (a)-[r:RESPONDS_TO]->(m)
                        SET r.success_count = $success_count,
                            r.avg_outcome = $avg_outcome,
                            r.updated_at = datetime()
                        """,
                        archetype=record.get("archetype"),
                        mechanism=record.get("mechanism"),
                        success_count=record.get("success_count", 0),
                        avg_outcome=record.get("avg_outcome", 0.5),
                    )
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                return MaintenanceResult(
                    operation="success_path_analysis",
                    success=True,
                    records_processed=len(records),
                    data={"paths_analyzed": len(records)},
                    duration_ms=duration,
                )
                
        except Exception as e:
            return MaintenanceResult(
                operation="success_path_analysis",
                success=False,
                error=str(e),
            )
    
    async def _run_emergence_detection(self) -> MaintenanceResult:
        """Detect emerging patterns."""
        start = datetime.now(timezone.utc)
        
        try:
            async with self._driver.session() as session:
                result = await session.run(EMERGENCE_DETECTION_QUERY)
                records = await result.data()
                
                # Store emergence signals
                for record in records:
                    await session.run(
                        """
                        MERGE (e:EmergentPattern {
                            archetype: $archetype,
                            mechanism: $mechanism
                        })
                        SET e.improvement = $improvement,
                            e.recent_success_rate = $recent_rate,
                            e.detected_at = datetime()
                        """,
                        archetype=record.get("archetype"),
                        mechanism=record.get("mechanism"),
                        improvement=record.get("improvement", 0),
                        recent_rate=record.get("recent_success_rate", 0),
                    )
                
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                
                return MaintenanceResult(
                    operation="emergence_detection",
                    success=True,
                    records_processed=len(records),
                    data={
                        "patterns_found": len(records),
                        "emerging": records[:5] if records else [],
                    },
                    duration_ms=duration,
                )
                
        except Exception as e:
            return MaintenanceResult(
                operation="emergence_detection",
                success=False,
                error=str(e),
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get maintenance status."""
        return {
            "last_maintenance": self._last_maintenance.isoformat() if self._last_maintenance else None,
            "gds_available": self._gds_available,
            "driver_connected": self._driver is not None,
        }


# =============================================================================
# SINGLETON & TRIGGER
# =============================================================================

_service: Optional[GraphMaintenanceService] = None


def get_graph_maintenance_service(driver=None) -> GraphMaintenanceService:
    """Get singleton graph maintenance service."""
    global _service
    if _service is None:
        _service = GraphMaintenanceService(driver)
    elif driver and _service._driver is None:
        _service._driver = driver
    return _service


async def trigger_maintenance(driver=None) -> List[MaintenanceResult]:
    """
    Trigger graph maintenance.
    
    Called periodically by SynergyOrchestrator.
    """
    service = get_graph_maintenance_service(driver)
    
    if not service._driver:
        # Try to get driver
        try:
            from adam.graph_reasoning.bridge import InteractionBridge
            # Would need to get driver from somewhere...
        except Exception:
            pass
    
    if not service._driver:
        logger.warning("No Neo4j driver available for maintenance")
        return []
    
    return await service.run_full_maintenance()
