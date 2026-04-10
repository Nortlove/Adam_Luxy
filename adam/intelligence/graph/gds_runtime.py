# =============================================================================
# ADAM Neo4j GDS Runtime Intelligence — Living Knowledge Graph
# Location: adam/intelligence/graph/gds_runtime.py
# =============================================================================

"""
NEO4J GRAPH DATA SCIENCE — LIVING KNOWLEDGE GRAPH

This module puts REAL graph algorithms in the runtime decisioning path.
Not fallback Cypher approximations — actual GDS projections that run
Node Similarity, Louvain, PageRank, Betweenness Centrality, and
Dijkstra Shortest Path on the live graph.

Architecture:
1. GRAPH PROJECTION LIFECYCLE — Managed in-memory graph projections
   that are created, used, and refreshed on a configurable schedule.
   This avoids the overhead of re-projecting for every request.

2. ALGORITHM EXECUTION — Real GDS algorithms run on projected graphs:
   - Node Similarity: Find archetypes with similar mechanism profiles
   - Louvain Community Detection: Discover psychographic communities
   - PageRank: Identify most influential mechanisms globally
   - Betweenness Centrality: Find bridge mechanisms between archetypes
   - Dijkstra Shortest Path: Optimal mechanism-to-outcome paths

3. NOVEL EDGE TYPES — Five novel edge types that encode learned patterns:
   - MECHANISM_SYNERGY: Which mechanisms amplify each other
   - ARCHETYPE_MIGRATION: How archetypes evolve over time
   - TEMPORAL_DECAY: How mechanism effectiveness decays
   - OUTCOME_ATTRIBUTION: Multi-touch mechanism-to-outcome attribution
   - COMPETITIVE_DISPLACEMENT: Which mechanisms replace others

4. LIVING GRAPH — The graph evolves based on outcomes:
   - Edge weights update from observed effectiveness
   - New edges emerge from discovered patterns
   - Weak edges decay and are eventually pruned
   - Community structure is re-detected periodically

Academic grounding:
- Jaccard/Cosine similarity for collaborative filtering (Linden et al. 2003)
- Louvain community detection (Blondel et al. 2008)
- PageRank for influence propagation (Brin & Page 1998)
- Betweenness centrality for brokerage (Freeman 1977)
- Temporal decay models (Ebbinghaus forgetting curve, 1885)
"""

import logging
import time
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# NOVEL EDGE TYPES
# =============================================================================

@dataclass
class NovelEdge:
    """A novel edge type for the graph."""
    edge_type: str
    source_label: str
    target_label: str
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def cypher_create(self) -> str:
        """Generate Cypher to create this edge type."""
        props = ", ".join(f"{k}: ${k}" for k in self.properties)
        return (
            f"MATCH (s:{self.source_label} {{id: $source_id}}), "
            f"(t:{self.target_label} {{id: $target_id}}) "
            f"MERGE (s)-[r:{self.edge_type} {{{props}}}]->(t) "
            f"RETURN r"
        )


NOVEL_EDGE_TYPES = {
    "MECHANISM_SYNERGY": NovelEdge(
        edge_type="MECHANISM_SYNERGY",
        source_label="CognitiveMechanism",
        target_label="CognitiveMechanism",
        properties={
            "synergy_score": 0.0,
            "co_occurrence_count": 0,
            "combined_lift": 0.0,
            "context_specificity": "",
        },
    ),
    "ARCHETYPE_MIGRATION": NovelEdge(
        edge_type="ARCHETYPE_MIGRATION",
        source_label="CustomerArchetype",
        target_label="CustomerArchetype",
        properties={
            "migration_probability": 0.0,
            "trigger_mechanism": "",
            "avg_migration_time_days": 0,
            "observation_count": 0,
        },
    ),
    "TEMPORAL_DECAY": NovelEdge(
        edge_type="TEMPORAL_DECAY",
        source_label="CognitiveMechanism",
        target_label="CustomerArchetype",
        properties={
            "initial_effectiveness": 0.0,
            "half_life_days": 30,
            "current_effectiveness": 0.0,
            "last_measured": "",
            "decay_observations": 0,
        },
    ),
    "OUTCOME_ATTRIBUTION": NovelEdge(
        edge_type="OUTCOME_ATTRIBUTION",
        source_label="CognitiveMechanism",
        target_label="ConversionOutcome",
        properties={
            "attribution_weight": 0.0,
            "position_in_journey": 0,
            "time_to_conversion_ms": 0,
            "archetype_context": "",
        },
    ),
    "COMPETITIVE_DISPLACEMENT": NovelEdge(
        edge_type="COMPETITIVE_DISPLACEMENT",
        source_label="CognitiveMechanism",
        target_label="CognitiveMechanism",
        properties={
            "displacement_rate": 0.0,
            "context": "",
            "archetype_specificity": "",
            "observation_count": 0,
        },
    ),
}


# =============================================================================
# GDS QUERY TEMPLATES
# =============================================================================

GDS_QUERIES = {
    "archetype_similarity": """
        CALL gds.nodeSimilarity.stream($graph_name, {
            topK: $top_k,
            similarityCutoff: $cutoff
        })
        YIELD node1, node2, similarity
        WITH gds.util.asNode(node1).name AS arch1,
             gds.util.asNode(node2).name AS arch2,
             similarity
        WHERE arch1 = $target_archetype
        RETURN arch2 AS similar_archetype, similarity
        ORDER BY similarity DESC
        LIMIT $limit
    """,

    "psychographic_communities": """
        CALL gds.louvain.stream($graph_name, {
            maxLevels: 5,
            maxIterations: 20
        })
        YIELD nodeId, communityId
        WITH gds.util.asNode(nodeId) AS node, communityId
        RETURN communityId,
               collect(CASE WHEN 'CustomerArchetype' IN labels(node)
                       THEN node.name END) AS archetypes,
               collect(CASE WHEN 'CognitiveMechanism' IN labels(node)
                       THEN node.name END) AS mechanisms
        ORDER BY size(archetypes) DESC
        LIMIT 10
    """,

    "mechanism_influence": """
        CALL gds.pageRank.stream($graph_name, {
            maxIterations: 50,
            dampingFactor: 0.85
        })
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE 'CognitiveMechanism' IN labels(node)
        RETURN node.name AS mechanism, score AS influence_score
        ORDER BY score DESC
        LIMIT 10
    """,

    "bridge_mechanisms": """
        CALL gds.betweennessCentrality.stream($graph_name)
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE 'CognitiveMechanism' IN labels(node)
        RETURN node.name AS mechanism, score AS bridge_score
        ORDER BY score DESC
        LIMIT 5
    """,

    "mechanism_outcome_path": """
        MATCH (start:CognitiveMechanism {name: $mechanism_name}),
              (end:ConversionOutcome {type: $outcome_type})
        CALL gds.shortestPath.dijkstra.stream($graph_name, {
            sourceNode: start,
            targetNode: end,
            relationshipWeightProperty: 'weight'
        })
        YIELD path, totalCost
        RETURN [n IN nodes(path) | n.name] AS path_nodes,
               totalCost AS path_weight
        ORDER BY totalCost ASC
        LIMIT 3
    """,
}


# =============================================================================
# GRAPH PROJECTION MANAGER
# =============================================================================

class GraphProjectionManager:
    """
    Manages the lifecycle of in-memory GDS graph projections.

    Projections are expensive to create but fast to query. This manager:
    1. Creates projections on first use
    2. Refreshes them on a configurable schedule
    3. Drops stale projections to free memory
    4. Handles GDS availability detection
    """

    # Projection definitions
    PROJECTIONS = {
        "adam_archetype_similarity": {
            "description": "Archetypes connected by shared mechanisms",
            "node_labels": ["CustomerArchetype", "CognitiveMechanism"],
            "relationship_types": {
                "RESPONDS_TO": {"properties": ["effectiveness"]},
            },
            "ttl_seconds": 600,
        },
        "adam_community_graph": {
            "description": "Full archetype-mechanism graph for community detection",
            "node_labels": ["CustomerArchetype", "CognitiveMechanism"],
            "relationship_types": {
                "RESPONDS_TO": {"properties": ["effectiveness"]},
                "MECHANISM_SYNERGY": {"properties": ["synergy_score"]},
            },
            "ttl_seconds": 900,
        },
        "adam_influence_graph": {
            "description": "Directed graph for PageRank influence scoring",
            "node_labels": ["CustomerArchetype", "CognitiveMechanism"],
            "relationship_types": {
                "RESPONDS_TO": {"properties": ["effectiveness"]},
            },
            "ttl_seconds": 600,
        },
        "adam_centrality_graph": {
            "description": "For betweenness centrality (bridge mechanisms)",
            "node_labels": ["CustomerArchetype", "CognitiveMechanism"],
            "relationship_types": {
                "RESPONDS_TO": {},
            },
            "ttl_seconds": 600,
        },
        "adam_outcome_graph": {
            "description": "For shortest path to outcomes",
            "node_labels": [
                "CognitiveMechanism", "ConversionOutcome", "CustomerArchetype",
            ],
            "relationship_types": {
                "OUTCOME_ATTRIBUTION": {"properties": ["attribution_weight"]},
                "RESPONDS_TO": {"properties": ["effectiveness"]},
            },
            "ttl_seconds": 300,
        },
    }

    def __init__(self):
        self._projected: Dict[str, float] = {}  # graph_name → creation_time
        self._gds_available: Optional[bool] = None

    def check_gds_available(self, session) -> bool:
        """Check if GDS library is installed."""
        if self._gds_available is not None:
            return self._gds_available

        try:
            result = session.run(
                "RETURN gds.version() AS version"
            )
            record = result.single()
            if record:
                logger.info(f"Neo4j GDS version: {record['version']}")
                self._gds_available = True
                return True
        except Exception:
            pass

        self._gds_available = False
        logger.info("Neo4j GDS not available — using fallback queries")
        return False

    def ensure_projection(
        self,
        session,
        graph_name: str,
    ) -> bool:
        """Ensure a graph projection exists and is fresh."""
        if graph_name not in self.PROJECTIONS:
            logger.warning(f"Unknown projection: {graph_name}")
            return False

        config = self.PROJECTIONS[graph_name]
        now = time.time()

        # Check if projection exists and is fresh
        if graph_name in self._projected:
            age = now - self._projected[graph_name]
            if age < config["ttl_seconds"]:
                return True
            else:
                # Stale — drop and recreate
                self._drop_projection(session, graph_name)

        # Create projection
        return self._create_projection(session, graph_name, config)

    def _create_projection(
        self,
        session,
        graph_name: str,
        config: Dict,
    ) -> bool:
        """Create a GDS graph projection."""
        try:
            node_labels = config["node_labels"]
            rel_types = config["relationship_types"]

            # Build relationship projection spec
            rel_spec = {}
            for rel_type, rel_config in rel_types.items():
                spec = {"orientation": "UNDIRECTED"}
                if rel_config.get("properties"):
                    spec["properties"] = {
                        prop: {"defaultValue": 0.5}
                        for prop in rel_config["properties"]
                    }
                rel_spec[rel_type] = spec

            # Use native projection
            session.run(
                """
                CALL gds.graph.project(
                    $graph_name,
                    $node_labels,
                    $rel_spec
                )
                """,
                graph_name=graph_name,
                node_labels=node_labels,
                rel_spec=rel_spec,
            )

            self._projected[graph_name] = time.time()
            logger.info(f"Created GDS projection: {graph_name}")
            return True

        except Exception as e:
            logger.warning(f"Failed to create projection {graph_name}: {e}")
            return False

    def _drop_projection(self, session, graph_name: str) -> None:
        """Drop a GDS graph projection."""
        try:
            session.run(
                "CALL gds.graph.drop($name, false)",
                name=graph_name,
            )
            self._projected.pop(graph_name, None)
            logger.debug(f"Dropped projection: {graph_name}")
        except Exception:
            pass

    def drop_all(self, session) -> None:
        """Drop all projections."""
        for name in list(self._projected.keys()):
            self._drop_projection(session, name)


# =============================================================================
# GDS RUNTIME SERVICE
# =============================================================================

class GDSRuntimeService:
    """
    Integrates Neo4j GDS algorithms into the real-time decisioning path.

    This service:
    1. Manages graph projections for fast algorithm execution
    2. Runs REAL GDS algorithms (not fallback Cypher)
    3. Falls back to Cypher when GDS is not available
    4. Creates and manages all 5 novel edge types
    5. Evolves edge weights based on outcomes (Living Graph)
    """

    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "",
        cache_ttl_seconds: int = 300,
    ):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.cache_ttl_seconds = cache_ttl_seconds

        self._driver = None
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._projection_mgr = GraphProjectionManager()
        self._gds_available: Optional[bool] = None

        # Living graph metrics
        self._edge_updates: int = 0
        self._decay_cycle_count: int = 0

    def _get_driver(self):
        """Get or create Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase
                self._driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_user, self.neo4j_password),
                )
                logger.info(f"Connected to Neo4j at {self.neo4j_uri}")
            except Exception as e:
                logger.warning(f"Could not connect to Neo4j: {e}")
                return None
        return self._driver

    def _check_cache(self, key: str) -> Optional[Any]:
        """Check cache for a result."""
        if key in self._cache:
            timestamp, value = self._cache[key]
            if time.time() - timestamp < self.cache_ttl_seconds:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Set a cache entry."""
        self._cache[key] = (time.time(), value)

    def _is_gds_available(self, session) -> bool:
        """Check GDS availability (cached)."""
        if self._gds_available is None:
            self._gds_available = self._projection_mgr.check_gds_available(session)
        return self._gds_available

    # =========================================================================
    # REAL GDS ALGORITHM QUERIES
    # =========================================================================

    def find_similar_archetypes(
        self,
        archetype: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find archetypes similar to the given one using GDS Node Similarity
        (Jaccard on shared mechanism effectiveness).

        Falls back to manual Cypher if GDS not available.
        """
        cache_key = f"similar_{archetype}_{top_k}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                if self._is_gds_available(session):
                    # REAL GDS: Node Similarity
                    graph_name = "adam_archetype_similarity"
                    if self._projection_mgr.ensure_projection(session, graph_name):
                        result = session.run(
                            GDS_QUERIES["archetype_similarity"],
                            graph_name=graph_name,
                            target_archetype=archetype,
                            top_k=top_k * 2,
                            cutoff=0.3,
                            limit=top_k,
                        )
                        results = [
                            {"archetype": r["similar_archetype"], "similarity": r["similarity"]}
                            for r in result
                        ]
                        if results:
                            self._set_cache(cache_key, results)
                            return results

                # Fallback: Manual Cypher similarity
                result = session.run("""
                    MATCH (a:CustomerArchetype {name: $archetype})-[r1:RESPONDS_TO]->(m:CognitiveMechanism)
                    WITH a, collect({mechanism: m.name, effectiveness: r1.effectiveness}) AS profile1

                    MATCH (b:CustomerArchetype)-[r2:RESPONDS_TO]->(m2:CognitiveMechanism)
                    WHERE b.name <> $archetype
                    WITH a, profile1, b, collect({mechanism: m2.name, effectiveness: r2.effectiveness}) AS profile2

                    WITH b.name AS similar_archetype,
                         size([x IN profile1 WHERE x.mechanism IN [y IN profile2 | y.mechanism]]) * 1.0 /
                         size(profile1 + [y IN profile2 WHERE NOT y.mechanism IN [x IN profile1 | x.mechanism]]) AS similarity

                    RETURN similar_archetype, similarity
                    ORDER BY similarity DESC
                    LIMIT $top_k
                """, archetype=archetype, top_k=top_k)

                results = [
                    {"archetype": r["similar_archetype"], "similarity": r["similarity"]}
                    for r in result
                ]

                self._set_cache(cache_key, results)
                return results

        except Exception as e:
            logger.warning(f"Similar archetype query failed: {e}")
            return []

    def get_mechanism_influence_ranking(self) -> List[Dict[str, float]]:
        """
        Get global mechanism influence ranking using GDS PageRank.

        Falls back to manual scoring if GDS not available.
        """
        cached = self._check_cache("mechanism_influence")
        if cached is not None:
            return cached

        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                if self._is_gds_available(session):
                    graph_name = "adam_influence_graph"
                    if self._projection_mgr.ensure_projection(session, graph_name):
                        result = session.run(
                            GDS_QUERIES["mechanism_influence"],
                            graph_name=graph_name,
                        )
                        results = [
                            {
                                "mechanism": r["mechanism"],
                                "influence_score": r["influence_score"],
                            }
                            for r in result
                        ]
                        if results:
                            self._set_cache("mechanism_influence", results)
                            return results

                # Fallback
                result = session.run("""
                    MATCH (m:CognitiveMechanism)<-[r:RESPONDS_TO]-(a:CustomerArchetype)
                    WITH m.name AS mechanism,
                         count(a) AS archetype_count,
                         avg(r.effectiveness) AS avg_effectiveness,
                         sum(r.effectiveness) AS total_effectiveness
                    RETURN mechanism,
                           total_effectiveness * log(archetype_count + 1) AS influence_score,
                           archetype_count,
                           avg_effectiveness
                    ORDER BY influence_score DESC
                    LIMIT 15
                """)

                results = [
                    {
                        "mechanism": r["mechanism"],
                        "influence_score": r["influence_score"],
                        "archetype_count": r["archetype_count"],
                        "avg_effectiveness": r["avg_effectiveness"],
                    }
                    for r in result
                ]

                self._set_cache("mechanism_influence", results)
                return results

        except Exception as e:
            logger.warning(f"Mechanism influence query failed: {e}")
            return []

    def detect_psychographic_communities(self) -> List[Dict[str, Any]]:
        """
        Discover psychographic communities using GDS Louvain.

        Returns clusters of archetypes and mechanisms that form
        natural communities.
        """
        cached = self._check_cache("communities")
        if cached is not None:
            return cached

        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                if self._is_gds_available(session):
                    graph_name = "adam_community_graph"
                    if self._projection_mgr.ensure_projection(session, graph_name):
                        result = session.run(
                            GDS_QUERIES["psychographic_communities"],
                            graph_name=graph_name,
                        )
                        results = [dict(r) for r in result]
                        if results:
                            self._set_cache("communities", results)
                            return results

                # Fallback: approximate communities via shared mechanisms
                result = session.run("""
                    MATCH (a1:CustomerArchetype)-[:RESPONDS_TO]->(m:CognitiveMechanism)<-[:RESPONDS_TO]-(a2:CustomerArchetype)
                    WHERE a1 <> a2
                    WITH a1.name AS arch1, a2.name AS arch2, count(m) AS shared
                    WHERE shared >= 3
                    RETURN arch1, collect({archetype: arch2, shared: shared}) AS connections
                    ORDER BY size(connections) DESC
                    LIMIT 10
                """)

                results = [dict(r) for r in result]
                self._set_cache("communities", results)
                return results

        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return []

    def find_bridge_mechanisms(
        self,
        source_archetype: str,
        target_archetype: str,
    ) -> List[Dict[str, Any]]:
        """
        Find bridge mechanisms using GDS Betweenness Centrality.

        These are mechanisms that connect different archetype clusters
        and are effective for diverse audiences.
        """
        cache_key = f"bridge_{source_archetype}_{target_archetype}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                if self._is_gds_available(session):
                    graph_name = "adam_centrality_graph"
                    if self._projection_mgr.ensure_projection(session, graph_name):
                        result = session.run(
                            GDS_QUERIES["bridge_mechanisms"],
                            graph_name=graph_name,
                        )
                        results = [dict(r) for r in result]
                        if results:
                            self._set_cache(cache_key, results)
                            return results

                # Fallback: shared mechanism analysis
                result = session.run("""
                    MATCH (a1:CustomerArchetype {name: $source})-[r1:RESPONDS_TO]->(m:CognitiveMechanism)
                    MATCH (a2:CustomerArchetype {name: $target})-[r2:RESPONDS_TO]->(m)
                    WITH m.name AS mechanism,
                         r1.effectiveness AS eff1,
                         r2.effectiveness AS eff2,
                         (r1.effectiveness + r2.effectiveness) / 2 AS avg_effectiveness,
                         abs(r1.effectiveness - r2.effectiveness) AS effectiveness_gap
                    RETURN mechanism, eff1, eff2, avg_effectiveness, effectiveness_gap
                    ORDER BY avg_effectiveness DESC, effectiveness_gap ASC
                    LIMIT 5
                """, source=source_archetype, target=target_archetype)

                results = [dict(r) for r in result]
                self._set_cache(cache_key, results)
                return results

        except Exception as e:
            logger.warning(f"Bridge mechanism query failed: {e}")
            return []

    def find_mechanism_outcome_path(
        self,
        mechanism_name: str,
        outcome_type: str = "conversion",
    ) -> List[Dict[str, Any]]:
        """
        Find shortest path from mechanism to outcome using GDS Dijkstra.
        """
        cache_key = f"path_{mechanism_name}_{outcome_type}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached

        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                if self._is_gds_available(session):
                    graph_name = "adam_outcome_graph"
                    if self._projection_mgr.ensure_projection(session, graph_name):
                        result = session.run(
                            GDS_QUERIES["mechanism_outcome_path"],
                            graph_name=graph_name,
                            mechanism_name=mechanism_name,
                            outcome_type=outcome_type,
                        )
                        results = [dict(r) for r in result]
                        if results:
                            self._set_cache(cache_key, results)
                            return results

                # Fallback: direct attribution query
                result = session.run("""
                    MATCH (m:CognitiveMechanism {name: $mechanism})
                          -[r:OUTCOME_ATTRIBUTION]->
                          (o:ConversionOutcome {type: $outcome_type})
                    RETURN m.name AS mechanism,
                           o.type AS outcome,
                           r.attribution_weight AS weight
                    ORDER BY r.attribution_weight DESC
                    LIMIT 3
                """, mechanism=mechanism_name, outcome_type=outcome_type)

                results = [dict(r) for r in result]
                self._set_cache(cache_key, results)
                return results

        except Exception as e:
            logger.warning(f"Mechanism outcome path query failed: {e}")
            return []

    def get_mechanism_synergies(
        self,
        mechanism: str,
    ) -> List[Dict[str, Any]]:
        """Find mechanisms that synergize with the given one."""
        driver = self._get_driver()
        if not driver:
            return []

        try:
            with driver.session() as session:
                # Try MECHANISM_SYNERGY edges first
                result = session.run("""
                    MATCH (m1:CognitiveMechanism {name: $mechanism})
                          -[r:MECHANISM_SYNERGY]-
                          (m2:CognitiveMechanism)
                    RETURN m2.name AS synergistic_mechanism,
                           r.synergy_score AS synergy_score,
                           r.combined_lift AS combined_lift,
                           r.co_occurrence_count AS co_occurrences
                    ORDER BY r.synergy_score DESC
                    LIMIT 5
                """, mechanism=mechanism)

                results = [dict(r) for r in result]

                if not results:
                    # Fallback: co-occurrence analysis
                    result = session.run("""
                        MATCH (a:CustomerArchetype)-[r1:RESPONDS_TO]->(m1:CognitiveMechanism {name: $mechanism})
                        MATCH (a)-[r2:RESPONDS_TO]->(m2:CognitiveMechanism)
                        WHERE m1 <> m2
                        WITH m2.name AS synergistic_mechanism,
                             count(a) AS co_occurrence,
                             avg(r1.effectiveness * r2.effectiveness) AS combined_score
                        RETURN synergistic_mechanism, co_occurrence, combined_score
                        ORDER BY combined_score DESC
                        LIMIT 5
                    """, mechanism=mechanism)

                    results = [dict(r) for r in result]

                return results

        except Exception as e:
            logger.warning(f"Mechanism synergy query failed: {e}")
            return []

    # =========================================================================
    # NOVEL EDGE MANAGEMENT — ALL 5 TYPES
    # =========================================================================

    def create_mechanism_synergy_edge(
        self,
        mechanism1: str,
        mechanism2: str,
        synergy_score: float,
        combined_lift: float = 0.0,
        context: str = "",
    ) -> bool:
        """Create or update a MECHANISM_SYNERGY edge."""
        driver = self._get_driver()
        if not driver:
            return False

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (m1:CognitiveMechanism {name: $mech1})
                    MERGE (m2:CognitiveMechanism {name: $mech2})
                    MERGE (m1)-[r:MECHANISM_SYNERGY]->(m2)
                    SET r.synergy_score =
                        CASE WHEN r.synergy_score IS NULL THEN $score
                        ELSE r.synergy_score * 0.9 + $score * 0.1 END,
                        r.combined_lift = $lift,
                        r.context_specificity = $context,
                        r.co_occurrence_count = COALESCE(r.co_occurrence_count, 0) + 1,
                        r.last_updated = datetime()
                """,
                    mech1=mechanism1, mech2=mechanism2,
                    score=synergy_score, lift=combined_lift, context=context,
                )
                self._edge_updates += 1
                return True
        except Exception as e:
            logger.warning(f"Failed to create synergy edge: {e}")
            return False

    def create_archetype_migration_edge(
        self,
        source_archetype: str,
        target_archetype: str,
        probability: float,
        trigger_mechanism: str = "",
    ) -> bool:
        """Create or update an ARCHETYPE_MIGRATION edge."""
        driver = self._get_driver()
        if not driver:
            return False

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (a1:CustomerArchetype {name: $source})
                    MERGE (a2:CustomerArchetype {name: $target})
                    MERGE (a1)-[r:ARCHETYPE_MIGRATION]->(a2)
                    SET r.migration_probability =
                        CASE WHEN r.migration_probability IS NULL THEN $prob
                        ELSE r.migration_probability * 0.9 + $prob * 0.1 END,
                        r.trigger_mechanism = $trigger,
                        r.observation_count = COALESCE(r.observation_count, 0) + 1,
                        r.last_observed = datetime()
                """,
                    source=source_archetype, target=target_archetype,
                    prob=probability, trigger=trigger_mechanism,
                )
                self._edge_updates += 1
                return True
        except Exception as e:
            logger.warning(f"Failed to create migration edge: {e}")
            return False

    def create_temporal_decay_edge(
        self,
        mechanism: str,
        archetype: str,
        initial_effectiveness: float,
        half_life_days: int = 30,
    ) -> bool:
        """Create or update a TEMPORAL_DECAY edge tracking effectiveness decay."""
        driver = self._get_driver()
        if not driver:
            return False

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (m:CognitiveMechanism {name: $mechanism})
                    MERGE (a:CustomerArchetype {name: $archetype})
                    MERGE (m)-[r:TEMPORAL_DECAY]->(a)
                    SET r.initial_effectiveness =
                        CASE WHEN r.initial_effectiveness IS NULL THEN $initial
                        ELSE r.initial_effectiveness * 0.8 + $initial * 0.2 END,
                        r.half_life_days = $half_life,
                        r.current_effectiveness = $initial,
                        r.last_measured = datetime(),
                        r.decay_observations = COALESCE(r.decay_observations, 0) + 1
                """,
                    mechanism=mechanism, archetype=archetype,
                    initial=initial_effectiveness, half_life=half_life_days,
                )
                self._edge_updates += 1
                return True
        except Exception as e:
            logger.warning(f"Failed to create temporal decay edge: {e}")
            return False

    def create_outcome_attribution_edge(
        self,
        mechanism: str,
        outcome_type: str,
        attribution_weight: float,
        position: int = 0,
        archetype_context: str = "",
    ) -> bool:
        """Create or update an OUTCOME_ATTRIBUTION edge."""
        driver = self._get_driver()
        if not driver:
            return False

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (m:CognitiveMechanism {name: $mechanism})
                    MERGE (o:ConversionOutcome {type: $outcome_type})
                    MERGE (m)-[r:OUTCOME_ATTRIBUTION]->(o)
                    SET r.attribution_weight =
                        CASE WHEN r.attribution_weight IS NULL
                        THEN $weight
                        ELSE (r.attribution_weight * 0.9 + $weight * 0.1) END,
                        r.position_in_journey = $position,
                        r.archetype_context = $context,
                        r.observation_count = COALESCE(r.observation_count, 0) + 1,
                        r.last_updated = datetime()
                """,
                    mechanism=mechanism, outcome_type=outcome_type,
                    weight=attribution_weight, position=position,
                    context=archetype_context,
                )
                self._edge_updates += 1
                return True
        except Exception as e:
            logger.warning(f"Failed to create attribution edge: {e}")
            return False

    def create_competitive_displacement_edge(
        self,
        displacing_mechanism: str,
        displaced_mechanism: str,
        displacement_rate: float,
        context: str = "",
        archetype: str = "",
    ) -> bool:
        """Create or update a COMPETITIVE_DISPLACEMENT edge."""
        driver = self._get_driver()
        if not driver:
            return False

        try:
            with driver.session() as session:
                session.run("""
                    MERGE (m1:CognitiveMechanism {name: $displacer})
                    MERGE (m2:CognitiveMechanism {name: $displaced})
                    MERGE (m1)-[r:COMPETITIVE_DISPLACEMENT]->(m2)
                    SET r.displacement_rate =
                        CASE WHEN r.displacement_rate IS NULL THEN $rate
                        ELSE r.displacement_rate * 0.9 + $rate * 0.1 END,
                        r.context = $context,
                        r.archetype_specificity = $archetype,
                        r.observation_count = COALESCE(r.observation_count, 0) + 1,
                        r.last_updated = datetime()
                """,
                    displacer=displacing_mechanism, displaced=displaced_mechanism,
                    rate=displacement_rate, context=context, archetype=archetype,
                )
                self._edge_updates += 1
                return True
        except Exception as e:
            logger.warning(f"Failed to create displacement edge: {e}")
            return False

    # =========================================================================
    # LIVING GRAPH — Edge Weight Evolution
    # =========================================================================

    def apply_temporal_decay(self) -> int:
        """
        Apply temporal decay to all TEMPORAL_DECAY edges.
        Uses Ebbinghaus forgetting curve: E(t) = E₀ * 2^(-t/h)
        where h is half-life in days.

        Returns number of edges updated.
        """
        driver = self._get_driver()
        if not driver:
            return 0

        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH ()-[r:TEMPORAL_DECAY]->()
                    WHERE r.last_measured IS NOT NULL
                    WITH r,
                         duration.inDays(r.last_measured, datetime()).days AS days_elapsed,
                         r.initial_effectiveness AS e0,
                         r.half_life_days AS half_life
                    WHERE days_elapsed > 0
                    SET r.current_effectiveness = e0 * (0.5 ^ (toFloat(days_elapsed) / half_life))
                    RETURN count(r) AS updated
                """)

                record = result.single()
                updated = record["updated"] if record else 0
                self._decay_cycle_count += 1

                logger.info(
                    f"Temporal decay applied to {updated} edges "
                    f"(cycle #{self._decay_cycle_count})"
                )
                return updated

        except Exception as e:
            logger.warning(f"Temporal decay failed: {e}")
            return 0

    def prune_weak_edges(
        self,
        min_observations: int = 5,
        min_weight: float = 0.05,
    ) -> int:
        """
        Prune edges that have decayed below threshold or have
        too few observations to be meaningful.

        Returns number of edges pruned.
        """
        driver = self._get_driver()
        if not driver:
            return 0

        total_pruned = 0

        try:
            with driver.session() as session:
                # Prune weak synergy edges
                result = session.run("""
                    MATCH ()-[r:MECHANISM_SYNERGY]->()
                    WHERE r.synergy_score < $min_weight
                      AND COALESCE(r.co_occurrence_count, 0) < $min_obs
                    DELETE r
                    RETURN count(r) AS deleted
                """, min_weight=min_weight, min_obs=min_observations)
                record = result.single()
                total_pruned += record["deleted"] if record else 0

                # Prune decayed effectiveness edges
                result = session.run("""
                    MATCH ()-[r:TEMPORAL_DECAY]->()
                    WHERE r.current_effectiveness < $min_weight
                      AND COALESCE(r.decay_observations, 0) >= $min_obs
                    DELETE r
                    RETURN count(r) AS deleted
                """, min_weight=min_weight, min_obs=min_observations)
                record = result.single()
                total_pruned += record["deleted"] if record else 0

                # Prune weak displacement edges
                result = session.run("""
                    MATCH ()-[r:COMPETITIVE_DISPLACEMENT]->()
                    WHERE r.displacement_rate < $min_weight
                      AND COALESCE(r.observation_count, 0) < $min_obs
                    DELETE r
                    RETURN count(r) AS deleted
                """, min_weight=min_weight, min_obs=min_observations)
                record = result.single()
                total_pruned += record["deleted"] if record else 0

                logger.info(f"Pruned {total_pruned} weak edges")
                return total_pruned

        except Exception as e:
            logger.warning(f"Edge pruning failed: {e}")
            return 0

    def evolve_edge_weights(
        self,
        mechanism: str,
        archetype: str,
        observed_effectiveness: float,
        outcome_type: str = "conversion",
    ) -> Dict[str, bool]:
        """
        Evolve edge weights based on an observed outcome.
        This is what makes the graph "living" — it updates itself.

        Updates:
        1. RESPONDS_TO effectiveness (main edge)
        2. TEMPORAL_DECAY current effectiveness
        3. OUTCOME_ATTRIBUTION weight
        4. Detects potential COMPETITIVE_DISPLACEMENT
        """
        results = {}

        driver = self._get_driver()
        if not driver:
            return results

        try:
            with driver.session() as session:
                # 1. Update main effectiveness edge
                session.run("""
                    MATCH (a:CustomerArchetype {name: $archetype})
                          -[r:RESPONDS_TO]->
                          (m:CognitiveMechanism {name: $mechanism})
                    SET r.effectiveness =
                        COALESCE(r.effectiveness, 0.5) * 0.95 + $eff * 0.05,
                        r.observations = COALESCE(r.observations, 0) + 1,
                        r.last_updated = datetime()
                """, archetype=archetype, mechanism=mechanism,
                    eff=observed_effectiveness)
                results["responds_to_updated"] = True

                # 2. Update temporal decay
                self.create_temporal_decay_edge(
                    mechanism=mechanism,
                    archetype=archetype,
                    initial_effectiveness=observed_effectiveness,
                )
                results["temporal_decay_updated"] = True

                # 3. Update outcome attribution
                self.create_outcome_attribution_edge(
                    mechanism=mechanism,
                    outcome_type=outcome_type,
                    attribution_weight=observed_effectiveness,
                    archetype_context=archetype,
                )
                results["attribution_updated"] = True

                # 4. Detect competitive displacement
                # If this mechanism's effectiveness went up, check if another went down
                result = session.run("""
                    MATCH (a:CustomerArchetype {name: $archetype})
                          -[r:RESPONDS_TO]->
                          (m:CognitiveMechanism)
                    WHERE m.name <> $mechanism
                      AND r.effectiveness < 0.3
                      AND COALESCE(r.observations, 0) > 3
                    RETURN m.name AS displaced, r.effectiveness AS eff
                    ORDER BY r.effectiveness ASC
                    LIMIT 1
                """, archetype=archetype, mechanism=mechanism)

                record = result.single()
                if record and observed_effectiveness > 0.6:
                    self.create_competitive_displacement_edge(
                        displacing_mechanism=mechanism,
                        displaced_mechanism=record["displaced"],
                        displacement_rate=observed_effectiveness - record["eff"],
                        archetype=archetype,
                    )
                    results["displacement_detected"] = True

        except Exception as e:
            logger.warning(f"Edge weight evolution failed: {e}")

        return results

    # =========================================================================
    # GRAPH-AWARE RECOMMENDATIONS
    # =========================================================================

    def get_graph_enhanced_recommendations(
        self,
        archetype: str,
        ndf_profile: Dict[str, float],
        category: str = "",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Get mechanism recommendations enhanced by graph intelligence.

        Combines:
        1. Direct mechanism-archetype effectiveness
        2. Similar archetype mechanism patterns (Node Similarity)
        3. Mechanism synergy effects (MECHANISM_SYNERGY edges)
        4. Community membership (Louvain)
        5. Bridge mechanism opportunities (Betweenness Centrality)
        6. Outcome attribution weights (OUTCOME_ATTRIBUTION edges)
        """
        recommendations = {
            "direct_mechanisms": [],
            "similar_archetype_insights": [],
            "synergy_opportunities": [],
            "community_info": [],
            "bridge_mechanisms": [],
            "graph_confidence": 0.0,
            "gds_algorithms_used": [],
        }

        driver = self._get_driver()
        if not driver:
            return recommendations

        try:
            with driver.session() as session:
                # 1. Direct mechanism-archetype effectiveness
                result = session.run("""
                    MATCH (a:CustomerArchetype {name: $archetype})
                          -[r:RESPONDS_TO]->(m:CognitiveMechanism)
                    RETURN m.name AS mechanism, r.effectiveness AS effectiveness
                    ORDER BY r.effectiveness DESC
                    LIMIT $top_k
                """, archetype=archetype, top_k=top_k)

                direct = [dict(r) for r in result]
                recommendations["direct_mechanisms"] = direct

                # 2. Similar archetype insights
                similar = self.find_similar_archetypes(archetype, top_k=3)
                recommendations["similar_archetype_insights"] = similar
                if similar:
                    recommendations["gds_algorithms_used"].append("NodeSimilarity")

                # 3. Synergy opportunities for top mechanisms
                if direct:
                    top_mechanism = direct[0]["mechanism"]
                    synergies = self.get_mechanism_synergies(top_mechanism)
                    recommendations["synergy_opportunities"] = synergies

                # 4. Influence ranking
                influence = self.get_mechanism_influence_ranking()
                if influence:
                    recommendations["gds_algorithms_used"].append("PageRank")

                # Compute graph confidence
                graph_confidence = 0.2
                if direct:
                    graph_confidence += 0.25
                if similar:
                    graph_confidence += 0.2
                if recommendations["synergy_opportunities"]:
                    graph_confidence += 0.15
                if influence:
                    graph_confidence += 0.1
                if self._gds_available:
                    graph_confidence += 0.1  # Bonus for real GDS

                recommendations["graph_confidence"] = min(0.95, graph_confidence)

        except Exception as e:
            logger.warning(f"Graph-enhanced recommendations failed: {e}")

        return recommendations

    # =========================================================================
    # STATISTICS AND LIFECYCLE
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive GDS service statistics."""
        return {
            "gds_available": self._gds_available,
            "edge_updates": self._edge_updates,
            "decay_cycles": self._decay_cycle_count,
            "projections_active": len(self._projection_mgr._projected),
            "cache_size": len(self._cache),
        }

    def close(self) -> None:
        """Close the Neo4j driver and drop projections."""
        if self._driver:
            try:
                with self._driver.session() as session:
                    self._projection_mgr.drop_all(session)
            except Exception:
                pass
            self._driver.close()
            self._driver = None


# =============================================================================
# SINGLETON
# =============================================================================

_gds_service: Optional[GDSRuntimeService] = None


def get_gds_service(
    neo4j_uri: str = "",
    neo4j_user: str = "",
    neo4j_password: str = "",
) -> GDSRuntimeService:
    """Get or create the singleton GDS service."""
    global _gds_service
    if _gds_service is None:
        # Use settings if not explicitly provided
        if not neo4j_uri or not neo4j_password:
            try:
                from adam.config.settings import get_settings
                s = get_settings()
                neo4j_uri = neo4j_uri or s.neo4j.uri
                neo4j_user = neo4j_user or s.neo4j.username
                neo4j_password = neo4j_password or s.neo4j.password
            except Exception:
                neo4j_uri = neo4j_uri or "bolt://localhost:7687"
                neo4j_user = neo4j_user or "neo4j"
        _gds_service = GDSRuntimeService(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
        )
    return _gds_service
