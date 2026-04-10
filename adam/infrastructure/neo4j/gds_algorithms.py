# =============================================================================
# ADAM Neo4j: Graph Data Science Algorithms
# Location: adam/infrastructure/neo4j/gds_algorithms.py
# =============================================================================

"""
GRAPH DATA SCIENCE ALGORITHMS

Implements Neo4j GDS algorithms for advanced graph intelligence:

1. PageRank - Identify influential constructs and mechanisms
2. Community Detection - Discover knowledge clusters
3. Node Similarity - Find related knowledge
4. Link Prediction - Suggest new hypotheses
5. Node Embeddings - Enable semantic similarity

These algorithms transform the knowledge graph from a passive store
into an active intelligence layer that discovers relationships.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# GDS PROJECTION DEFINITIONS
# =============================================================================

# Knowledge graph projection for GDS
KNOWLEDGE_GRAPH_PROJECTION = """
CALL gds.graph.project(
    'knowledge-graph',
    ['BehavioralKnowledge', 'PsychologicalConstruct', 'BehavioralSignal', 
     'AdvertisingKnowledge', 'ResearchDomain', 'ConfidenceTier'],
    {
        MAPS_TO: {properties: ['effect_size']},
        DERIVED_FROM: {properties: ['feature_name']},
        BELONGS_TO: {},
        HAS_CONFIDENCE: {},
        TESTS_MECHANISM: {},
        VALIDATED_BY: {}
    }
)
"""

# User behavior graph projection
USER_BEHAVIOR_PROJECTION = """
CALL gds.graph.project(
    'user-behavior-graph',
    ['User', 'Session', 'Decision', 'Outcome', 'AdCreative'],
    {
        HAD_SESSION: {},
        MADE_DECISION: {},
        RESULTED_IN: {},
        SHOWN_AD: {}
    }
)
"""


# =============================================================================
# GDS ALGORITHM RUNNER
# =============================================================================

class GDSAlgorithmRunner:
    """
    Runs Neo4j Graph Data Science algorithms.
    
    Provides methods for:
    - Graph projections management
    - Centrality algorithms (PageRank, Betweenness)
    - Community detection (Louvain, Label Propagation)
    - Similarity algorithms (Node Similarity)
    - Link prediction (Adamic Adar, Common Neighbors)
    - Node embeddings (Node2Vec, FastRP)
    
    Usage:
        runner = GDSAlgorithmRunner(neo4j_driver)
        await runner.ensure_projection("knowledge-graph")
        
        pagerank = await runner.run_pagerank("knowledge-graph")
        communities = await runner.run_community_detection("knowledge-graph")
    """
    
    def __init__(self, driver):
        self.driver = driver
        self.active_projections: Dict[str, datetime] = {}
    
    # =========================================================================
    # PROJECTION MANAGEMENT
    # =========================================================================
    
    async def create_knowledge_graph_projection(self) -> bool:
        """Create the knowledge graph projection for GDS."""
        query = """
        CALL gds.graph.project(
            'knowledge-graph',
            {
                BehavioralKnowledge: {properties: ['tier', 'effect_size']},
                PsychologicalConstruct: {},
                BehavioralSignal: {},
                AdvertisingKnowledge: {properties: ['tier', 'effect_size']},
                ResearchDomain: {},
                CognitiveMechanism: {}
            },
            {
                MAPS_TO: {properties: ['effect_size', 'direction']},
                DERIVED_FROM: {},
                BELONGS_TO: {},
                TESTS_MECHANISM: {}
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                record = await result.single()
                
                if record:
                    self.active_projections["knowledge-graph"] = datetime.utcnow()
                    logger.info(
                        f"Created knowledge-graph projection: "
                        f"{record['nodeCount']} nodes, {record['relationshipCount']} rels"
                    )
                    return True
        except Exception as e:
            if "already exists" in str(e):
                logger.info("knowledge-graph projection already exists")
                self.active_projections["knowledge-graph"] = datetime.utcnow()
                return True
            logger.error(f"Failed to create knowledge-graph projection: {e}")
        
        return False
    
    async def drop_projection(self, graph_name: str) -> bool:
        """Drop a graph projection."""
        query = f"CALL gds.graph.drop('{graph_name}')"
        
        try:
            async with self.driver.session() as session:
                await session.run(query)
                self.active_projections.pop(graph_name, None)
                logger.info(f"Dropped projection: {graph_name}")
                return True
        except Exception as e:
            logger.warning(f"Failed to drop projection {graph_name}: {e}")
            return False
    
    async def ensure_projection(self, graph_name: str = "knowledge-graph") -> bool:
        """Ensure a projection exists, creating if necessary."""
        if graph_name in self.active_projections:
            return True
        
        if graph_name == "knowledge-graph":
            return await self.create_knowledge_graph_projection()
        
        return False
    
    # =========================================================================
    # CENTRALITY ALGORITHMS
    # =========================================================================
    
    async def run_pagerank(
        self,
        graph_name: str = "knowledge-graph",
        damping_factor: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 0.0001,
    ) -> List[Dict[str, Any]]:
        """
        Run PageRank to identify influential nodes.
        
        High PageRank constructs are central to the knowledge graph -
        they are referenced by many other knowledge items.
        
        Returns:
            List of nodes with PageRank scores
        """
        await self.ensure_projection(graph_name)
        
        query = f"""
        CALL gds.pageRank.stream('{graph_name}', {{
            dampingFactor: $damping_factor,
            maxIterations: $max_iterations,
            tolerance: $tolerance
        }})
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE score > 0.01
        RETURN 
            labels(node)[0] AS label,
            node.name AS name,
            node.knowledge_id AS id,
            score
        ORDER BY score DESC
        LIMIT 100
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    damping_factor=damping_factor,
                    max_iterations=max_iterations,
                    tolerance=tolerance,
                )
                records = await result.data()
                
                logger.info(f"PageRank completed: {len(records)} influential nodes found")
                return records
        except Exception as e:
            logger.error(f"PageRank failed: {e}")
            return []
    
    async def run_betweenness_centrality(
        self,
        graph_name: str = "knowledge-graph",
        sampling_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run Betweenness Centrality to find bridging nodes.
        
        High betweenness nodes connect different knowledge clusters -
        they are key for transfer learning and cross-domain insights.
        
        Returns:
            List of nodes with betweenness scores
        """
        await self.ensure_projection(graph_name)
        
        sampling_config = f"samplingSize: {sampling_size}," if sampling_size else ""
        
        query = f"""
        CALL gds.betweenness.stream('{graph_name}', {{
            {sampling_config}
            concurrency: 4
        }})
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE score > 0
        RETURN 
            labels(node)[0] AS label,
            node.name AS name,
            node.knowledge_id AS id,
            score
        ORDER BY score DESC
        LIMIT 50
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                logger.info(f"Betweenness centrality: {len(records)} bridging nodes found")
                return records
        except Exception as e:
            logger.error(f"Betweenness centrality failed: {e}")
            return []
    
    # =========================================================================
    # COMMUNITY DETECTION
    # =========================================================================
    
    async def run_louvain(
        self,
        graph_name: str = "knowledge-graph",
        include_intermediate: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Run Louvain community detection.
        
        Discovers natural clusters in the knowledge graph -
        groups of related knowledge that should be used together.
        
        Returns:
            List of nodes with community assignments
        """
        await self.ensure_projection(graph_name)
        
        query = f"""
        CALL gds.louvain.stream('{graph_name}', {{
            includeIntermediateCommunities: $include_intermediate,
            concurrency: 4
        }})
        YIELD nodeId, communityId, intermediateCommunityIds
        WITH gds.util.asNode(nodeId) AS node, communityId
        RETURN 
            communityId,
            labels(node)[0] AS label,
            node.name AS name,
            node.knowledge_id AS id
        ORDER BY communityId, label
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    include_intermediate=include_intermediate,
                )
                records = await result.data()
                
                # Group by community
                communities = {}
                for record in records:
                    cid = record["communityId"]
                    if cid not in communities:
                        communities[cid] = []
                    communities[cid].append(record)
                
                logger.info(f"Louvain: {len(communities)} communities found")
                return records
        except Exception as e:
            logger.error(f"Louvain failed: {e}")
            return []
    
    async def get_community_summary(
        self,
        graph_name: str = "knowledge-graph",
    ) -> List[Dict[str, Any]]:
        """
        Get summary of detected communities.
        
        Returns community IDs with sizes and representative members.
        """
        await self.ensure_projection(graph_name)
        
        query = f"""
        CALL gds.louvain.stream('{graph_name}')
        YIELD nodeId, communityId
        WITH communityId, collect(gds.util.asNode(nodeId)) AS members
        RETURN 
            communityId,
            size(members) AS size,
            [m IN members[..5] | m.name] AS sample_members
        ORDER BY size DESC
        LIMIT 20
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Community summary failed: {e}")
            return []
    
    # =========================================================================
    # SIMILARITY ALGORITHMS
    # =========================================================================
    
    async def run_node_similarity(
        self,
        graph_name: str = "knowledge-graph",
        similarity_cutoff: float = 0.5,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Run Node Similarity to find related knowledge.
        
        Similar nodes share many neighbors - they are conceptually related.
        Useful for finding redundant knowledge or suggesting connections.
        
        Returns:
            List of node pairs with similarity scores
        """
        await self.ensure_projection(graph_name)
        
        query = f"""
        CALL gds.nodeSimilarity.stream('{graph_name}', {{
            similarityCutoff: $cutoff,
            topK: $top_k
        }})
        YIELD node1, node2, similarity
        WITH gds.util.asNode(node1) AS n1, 
             gds.util.asNode(node2) AS n2, 
             similarity
        RETURN 
            n1.name AS node1_name,
            n1.knowledge_id AS node1_id,
            labels(n1)[0] AS node1_type,
            n2.name AS node2_name,
            n2.knowledge_id AS node2_id,
            labels(n2)[0] AS node2_type,
            similarity
        ORDER BY similarity DESC
        LIMIT 100
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    cutoff=similarity_cutoff,
                    top_k=top_k,
                )
                records = await result.data()
                
                logger.info(f"Node similarity: {len(records)} similar pairs found")
                return records
        except Exception as e:
            logger.error(f"Node similarity failed: {e}")
            return []
    
    # =========================================================================
    # LINK PREDICTION
    # =========================================================================
    
    async def run_link_prediction(
        self,
        graph_name: str = "knowledge-graph",
        algorithm: str = "adamic_adar",
    ) -> List[Dict[str, Any]]:
        """
        Run link prediction to suggest new relationships.
        
        Predicts which nodes should be connected but aren't -
        suggests new hypotheses for the knowledge system.
        
        Args:
            algorithm: "adamic_adar" or "common_neighbors"
            
        Returns:
            List of predicted links with scores
        """
        await self.ensure_projection(graph_name)
        
        if algorithm == "adamic_adar":
            algo_call = "gds.alpha.linkprediction.adamicAdar"
        else:
            algo_call = "gds.alpha.linkprediction.commonNeighbors"
        
        # Find node pairs without direct connection
        query = f"""
        MATCH (n1:BehavioralKnowledge), (n2:PsychologicalConstruct)
        WHERE NOT (n1)-[:MAPS_TO]-(n2)
        WITH n1, n2, {algo_call}(n1, n2) AS score
        WHERE score > 0
        RETURN 
            n1.name AS knowledge_name,
            n1.knowledge_id AS knowledge_id,
            n2.name AS construct_name,
            score
        ORDER BY score DESC
        LIMIT 50
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                logger.info(f"Link prediction: {len(records)} potential links found")
                return records
        except Exception as e:
            logger.error(f"Link prediction failed: {e}")
            return []
    
    # =========================================================================
    # NODE EMBEDDINGS
    # =========================================================================
    
    async def run_node2vec(
        self,
        graph_name: str = "knowledge-graph",
        embedding_dimension: int = 128,
        walk_length: int = 80,
        walks_per_node: int = 10,
        store_property: Optional[str] = "embedding",
    ) -> bool:
        """
        Run Node2Vec to generate node embeddings.
        
        Embeddings enable:
        - Semantic similarity queries
        - Clustering in embedding space
        - ML models on graph structure
        
        Args:
            store_property: If set, stores embeddings as node property
            
        Returns:
            Success status
        """
        await self.ensure_projection(graph_name)
        
        if store_property:
            query = f"""
            CALL gds.node2vec.write('{graph_name}', {{
                embeddingDimension: $dim,
                walkLength: $walk_length,
                walksPerNode: $walks_per_node,
                writeProperty: $property
            }})
            YIELD nodePropertiesWritten
            RETURN nodePropertiesWritten
            """
        else:
            query = f"""
            CALL gds.node2vec.stream('{graph_name}', {{
                embeddingDimension: $dim,
                walkLength: $walk_length,
                walksPerNode: $walks_per_node
            }})
            YIELD nodeId, embedding
            RETURN count(*) AS nodesEmbedded
            """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    dim=embedding_dimension,
                    walk_length=walk_length,
                    walks_per_node=walks_per_node,
                    property=store_property,
                )
                record = await result.single()
                
                if record:
                    count = record.get("nodePropertiesWritten") or record.get("nodesEmbedded")
                    logger.info(f"Node2Vec: {count} nodes embedded")
                    return True
        except Exception as e:
            logger.error(f"Node2Vec failed: {e}")
        
        return False
    
    async def find_similar_by_embedding(
        self,
        node_id: str,
        embedding_property: str = "embedding",
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find similar nodes using embedding similarity.
        
        Args:
            node_id: ID of the query node
            embedding_property: Property containing embedding
            top_k: Number of similar nodes to return
            
        Returns:
            List of similar nodes with scores
        """
        query = f"""
        MATCH (query {{knowledge_id: $node_id}})
        WHERE query.{embedding_property} IS NOT NULL
        MATCH (other)
        WHERE other.{embedding_property} IS NOT NULL
          AND other <> query
        WITH query, other,
             gds.similarity.cosine(query.{embedding_property}, other.{embedding_property}) AS similarity
        WHERE similarity > 0.5
        RETURN 
            other.name AS name,
            other.knowledge_id AS id,
            labels(other)[0] AS type,
            similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, node_id=node_id, top_k=top_k)
                records = await result.data()
                return records
        except Exception as e:
            logger.error(f"Embedding similarity search failed: {e}")
            return []
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def get_graph_stats(
        self,
        graph_name: str = "knowledge-graph",
    ) -> Dict[str, Any]:
        """Get statistics for a projected graph."""
        query = f"""
        CALL gds.graph.list('{graph_name}')
        YIELD graphName, nodeCount, relationshipCount, degreeDistribution
        RETURN graphName, nodeCount, relationshipCount, degreeDistribution
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                record = await result.single()
                
                if record:
                    return {
                        "name": record["graphName"],
                        "nodes": record["nodeCount"],
                        "relationships": record["relationshipCount"],
                        "degree_distribution": record["degreeDistribution"],
                    }
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
        
        return {}
    
    async def run_comprehensive_analysis(
        self,
        graph_name: str = "knowledge-graph",
    ) -> Dict[str, Any]:
        """
        Run comprehensive graph analysis.
        
        Returns PageRank, communities, and bridging nodes.
        """
        await self.ensure_projection(graph_name)
        
        results = {}
        
        # PageRank
        results["influential_nodes"] = await self.run_pagerank(graph_name)
        
        # Communities
        results["communities"] = await self.get_community_summary(graph_name)
        
        # Bridging nodes
        results["bridging_nodes"] = await self.run_betweenness_centrality(graph_name)
        
        # Stats
        results["stats"] = await self.get_graph_stats(graph_name)
        
        return results


# =============================================================================
# SINGLETON
# =============================================================================

_runner: Optional[GDSAlgorithmRunner] = None


def get_gds_runner(driver=None) -> GDSAlgorithmRunner:
    """Get singleton GDS runner."""
    global _runner
    if _runner is None:
        if driver is None:
            raise ValueError("Driver required for first initialization")
        _runner = GDSAlgorithmRunner(driver)
    return _runner
