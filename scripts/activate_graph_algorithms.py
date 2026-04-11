#!/usr/bin/env python3
"""
ACTIVATE GRAPH ALGORITHMS
=========================

Runs Neo4j Graph Data Science (GDS) algorithms to extract higher-level
intelligence patterns from the graph database.

Algorithms:
1. PageRank - Identify influential mechanisms and customers
2. Community Detection - Find archetype clusters
3. Similarity - Find similar products/customers
4. Path Analysis - Identify purchase journey patterns
5. Centrality - Find key connection points

Requirements:
- Neo4j with GDS plugin installed
- Data imported via import_reingestion_to_neo4j.py

Usage:
    python scripts/activate_graph_algorithms.py
    python scripts/activate_graph_algorithms.py --algorithm pagerank
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# GDS ALGORITHM QUERIES
# =============================================================================

ALGORITHM_QUERIES = {
    # =================================================================
    # PAGERANK - Find influential nodes
    # =================================================================
    "pagerank_mechanisms": {
        "description": "Find most influential persuasion mechanisms",
        "project_query": """
            CALL gds.graph.project(
                'mechanism_influence',
                ['Mechanism', 'Template', 'Archetype'],
                {
                    USES_MECHANISM: {type: 'USES_MECHANISM', orientation: 'UNDIRECTED'},
                    EFFECTIVE_FOR: {type: 'EFFECTIVE_FOR', orientation: 'UNDIRECTED'}
                }
            )
        """,
        "algorithm_query": """
            CALL gds.pageRank.stream('mechanism_influence')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE 'Mechanism' IN labels(node)
            RETURN node.name AS mechanism, score
            ORDER BY score DESC
            LIMIT 20
        """,
        "cleanup_query": "CALL gds.graph.drop('mechanism_influence', false)",
        "store_property": "pagerank_score",
    },
    
    "pagerank_templates": {
        "description": "Find most influential templates by connectivity",
        "project_query": """
            CALL gds.graph.project(
                'template_influence',
                ['PersuasiveTemplate', 'Archetype', 'Mechanism'],
                {
                    FOR_ARCHETYPE: {type: 'FOR_ARCHETYPE', orientation: 'UNDIRECTED'},
                    USES_MECHANISM: {type: 'USES_MECHANISM', orientation: 'UNDIRECTED'}
                }
            )
        """,
        "algorithm_query": """
            CALL gds.pageRank.stream('template_influence')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE 'PersuasiveTemplate' IN labels(node)
            RETURN node.pattern AS pattern, node.helpful_votes AS votes, score
            ORDER BY score DESC
            LIMIT 50
        """,
        "cleanup_query": "CALL gds.graph.drop('template_influence', false)",
        "store_property": "pagerank_score",
    },
    
    # =================================================================
    # COMMUNITY DETECTION - Find clusters
    # =================================================================
    "community_archetypes": {
        "description": "Detect archetype communities based on mechanism preferences",
        "project_query": """
            CALL gds.graph.project(
                'archetype_communities',
                ['Archetype', 'Mechanism'],
                {
                    EFFECTIVE_FOR: {
                        type: 'EFFECTIVE_FOR',
                        orientation: 'UNDIRECTED',
                        properties: ['effectiveness']
                    }
                }
            )
        """,
        "algorithm_query": """
            CALL gds.louvain.stream('archetype_communities')
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            WHERE 'Archetype' IN labels(node)
            RETURN communityId, collect(node.name) AS archetypes, count(*) AS size
            ORDER BY size DESC
        """,
        "cleanup_query": "CALL gds.graph.drop('archetype_communities', false)",
        "store_property": "community_id",
    },
    
    "community_mechanisms": {
        "description": "Detect mechanism clusters that often work together",
        "project_query": """
            CALL gds.graph.project(
                'mechanism_clusters',
                ['Mechanism', 'PersuasiveTemplate'],
                {
                    USES_MECHANISM: {type: 'USES_MECHANISM', orientation: 'UNDIRECTED'}
                }
            )
        """,
        "algorithm_query": """
            CALL gds.louvain.stream('mechanism_clusters')
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            WHERE 'Mechanism' IN labels(node)
            RETURN communityId, collect(node.name) AS mechanisms, count(*) AS size
            ORDER BY size DESC
        """,
        "cleanup_query": "CALL gds.graph.drop('mechanism_clusters', false)",
        "store_property": "cluster_id",
    },
    
    # =================================================================
    # BETWEENNESS CENTRALITY - Find bridges/gatekeepers
    # =================================================================
    "centrality_mechanisms": {
        "description": "Find mechanisms that bridge different archetypes",
        "project_query": """
            CALL gds.graph.project(
                'mechanism_centrality',
                ['Mechanism', 'Archetype', 'PersuasiveTemplate'],
                {
                    EFFECTIVE_FOR: {type: 'EFFECTIVE_FOR', orientation: 'UNDIRECTED'},
                    FOR_ARCHETYPE: {type: 'FOR_ARCHETYPE', orientation: 'UNDIRECTED'},
                    USES_MECHANISM: {type: 'USES_MECHANISM', orientation: 'UNDIRECTED'}
                }
            )
        """,
        "algorithm_query": """
            CALL gds.betweennessCentrality.stream('mechanism_centrality')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE 'Mechanism' IN labels(node)
            RETURN node.name AS mechanism, score AS betweenness
            ORDER BY score DESC
            LIMIT 15
        """,
        "cleanup_query": "CALL gds.graph.drop('mechanism_centrality', false)",
        "store_property": "betweenness_centrality",
    },
    
    # =================================================================
    # NODE SIMILARITY - Find similar entities
    # =================================================================
    "similarity_archetypes": {
        "description": "Find similar archetypes based on mechanism preferences",
        "project_query": """
            CALL gds.graph.project(
                'archetype_similarity',
                ['Archetype', 'Mechanism'],
                {
                    EFFECTIVE_FOR: {
                        type: 'EFFECTIVE_FOR',
                        orientation: 'NATURAL',
                        properties: ['effectiveness']
                    }
                }
            )
        """,
        "algorithm_query": """
            CALL gds.nodeSimilarity.stream('archetype_similarity')
            YIELD node1, node2, similarity
            WITH gds.util.asNode(node1) AS a1, gds.util.asNode(node2) AS a2, similarity
            WHERE 'Archetype' IN labels(a1) AND 'Archetype' IN labels(a2)
            RETURN a1.name AS archetype1, a2.name AS archetype2, similarity
            ORDER BY similarity DESC
            LIMIT 20
        """,
        "cleanup_query": "CALL gds.graph.drop('archetype_similarity', false)",
        "store_property": None,  # Creates relationships, not properties
    },
    
    # =================================================================
    # DEGREE CENTRALITY - Find well-connected nodes
    # =================================================================
    "degree_products": {
        "description": "Find products with most journey connections",
        "project_query": """
            CALL gds.graph.project(
                'product_degree',
                ['ProductIntelligence'],
                {
                    BOUGHT_WITH: {type: 'BOUGHT_WITH', orientation: 'UNDIRECTED'}
                }
            )
        """,
        "algorithm_query": """
            CALL gds.degree.stream('product_degree')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            RETURN node.asin AS asin, node.brand AS brand, score AS degree
            ORDER BY score DESC
            LIMIT 30
        """,
        "cleanup_query": "CALL gds.graph.drop('product_degree', false)",
        "store_property": "degree_centrality",
    },
}

# Simplified queries that don't require GDS (for systems without GDS installed)
SIMPLE_QUERIES = {
    "top_mechanisms_by_templates": {
        "description": "Find mechanisms with most high-vote templates",
        "query": """
            MATCH (t:PersuasiveTemplate)-[:USES_MECHANISM]->(m:Mechanism)
            WHERE t.helpful_votes > 10
            RETURN m.name AS mechanism, 
                   count(t) AS template_count,
                   avg(t.helpful_votes) AS avg_votes,
                   sum(t.helpful_votes) AS total_votes
            ORDER BY total_votes DESC
            LIMIT 20
        """,
    },
    
    "archetype_mechanism_pairs": {
        "description": "Find strongest archetype-mechanism combinations",
        "query": """
            MATCH (a:Archetype)-[r:RESPONDS_TO]->(m:Mechanism)
            WHERE r.effectiveness > 0.5
            RETURN a.name AS archetype, m.name AS mechanism, 
                   r.effectiveness AS effectiveness,
                   r.sample_size AS sample_size
            ORDER BY r.effectiveness DESC
            LIMIT 50
        """,
    },
    
    "template_clusters_by_archetype": {
        "description": "Count templates per archetype-mechanism",
        "query": """
            MATCH (t:PersuasiveTemplate)-[:FOR_ARCHETYPE]->(a:Archetype)
            MATCH (t)-[:USES_MECHANISM]->(m:Mechanism)
            RETURN a.name AS archetype, m.name AS mechanism,
                   count(t) AS template_count,
                   sum(t.helpful_votes) AS total_votes
            ORDER BY total_votes DESC
            LIMIT 100
        """,
    },
    
    "effectiveness_matrix_summary": {
        "description": "Summarize effectiveness scores",
        "query": """
            MATCH (e:EffectivenessScore)
            RETURN e.archetype AS archetype, e.mechanism AS mechanism,
                   e.effectiveness AS effectiveness, e.confidence AS confidence,
                   e.sample_size AS sample_size
            ORDER BY e.effectiveness * e.confidence DESC
            LIMIT 100
        """,
    },
}


# =============================================================================
# ALGORITHM RUNNER
# =============================================================================

class GraphAlgorithmRunner:
    """Runs GDS algorithms on Neo4j."""
    
    def __init__(self):
        self._driver = None
        self._gds_available = None
        self.results: Dict[str, Any] = {}
    
    async def connect(self):
        """Connect to Neo4j."""
        try:
            from adam.infrastructure.neo4j.driver import get_neo4j_driver
            self._driver = get_neo4j_driver()
            
            # Check if GDS is available
            async with self._driver.session() as session:
                result = await session.run("RETURN gds.version() AS version")
                record = await result.single()
                if record:
                    version = record["version"]
                    self._gds_available = True
                    logger.info(f"GDS version: {version}")
                else:
                    self._gds_available = False
                    
        except Exception as e:
            logger.warning(f"GDS not available: {e}")
            self._gds_available = False
    
    async def run_gds_algorithm(self, name: str, config: Dict) -> Dict[str, Any]:
        """Run a single GDS algorithm."""
        
        if not self._gds_available:
            logger.warning(f"GDS not available, skipping {name}")
            return {"error": "GDS not available"}
        
        result = {
            "algorithm": name,
            "description": config["description"],
            "success": False,
            "data": [],
        }
        
        try:
            async with self._driver.session() as session:
                # Step 1: Create projection
                logger.info(f"  Creating graph projection for {name}...")
                try:
                    await session.run(config["project_query"])
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        raise
                    # Graph already exists, drop and recreate
                    await session.run(config["cleanup_query"])
                    await session.run(config["project_query"])
                
                # Step 2: Run algorithm
                logger.info(f"  Running {name} algorithm...")
                algo_result = await session.run(config["algorithm_query"])
                records = await algo_result.data()
                result["data"] = records
                result["success"] = True
                
                # Step 3: Cleanup
                await session.run(config["cleanup_query"])
                
                logger.info(f"  {name}: {len(records)} results")
                
        except Exception as e:
            logger.error(f"  {name} failed: {e}")
            result["error"] = str(e)
        
        return result
    
    async def run_simple_query(self, name: str, config: Dict) -> Dict[str, Any]:
        """Run a simple Cypher query (no GDS required)."""
        
        result = {
            "query": name,
            "description": config["description"],
            "success": False,
            "data": [],
        }
        
        try:
            async with self._driver.session() as session:
                query_result = await session.run(config["query"])
                records = await query_result.data()
                result["data"] = records
                result["success"] = True
                logger.info(f"  {name}: {len(records)} results")
                
        except Exception as e:
            logger.error(f"  {name} failed: {e}")
            result["error"] = str(e)
        
        return result
    
    async def run_all_algorithms(self, include_gds: bool = True) -> Dict[str, Any]:
        """Run all algorithms and collect results."""
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "gds_available": self._gds_available,
            "gds_algorithms": {},
            "simple_queries": {},
        }
        
        # Run GDS algorithms if available and requested
        if include_gds and self._gds_available:
            logger.info("\nRunning GDS algorithms...")
            for name, config in ALGORITHM_QUERIES.items():
                result = await self.run_gds_algorithm(name, config)
                all_results["gds_algorithms"][name] = result
        
        # Always run simple queries
        logger.info("\nRunning simple queries...")
        for name, config in SIMPLE_QUERIES.items():
            result = await self.run_simple_query(name, config)
            all_results["simple_queries"][name] = result
        
        self.results = all_results
        return all_results
    
    def save_results(self, output_path: Path) -> None:
        """Save results to JSON file."""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Results saved to: {output_path}")


# =============================================================================
# INTELLIGENCE EXTRACTION
# =============================================================================

def extract_intelligence_insights(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract actionable intelligence from algorithm results.
    
    This creates the higher-level patterns that inform decisions.
    """
    insights = {
        "influential_mechanisms": [],
        "archetype_clusters": [],
        "bridge_mechanisms": [],  # Connect different archetypes
        "similar_archetypes": [],
        "universal_patterns": [],
    }
    
    # Extract from GDS results
    gds = results.get("gds_algorithms", {})
    
    # Influential mechanisms from PageRank
    pagerank = gds.get("pagerank_mechanisms", {})
    if pagerank.get("success"):
        insights["influential_mechanisms"] = [
            {"mechanism": r["mechanism"], "influence_score": r["score"]}
            for r in pagerank.get("data", [])[:10]
        ]
    
    # Archetype clusters from community detection
    communities = gds.get("community_archetypes", {})
    if communities.get("success"):
        insights["archetype_clusters"] = [
            {"cluster_id": r["communityId"], "archetypes": r["archetypes"], "size": r["size"]}
            for r in communities.get("data", [])
        ]
    
    # Bridge mechanisms from centrality
    centrality = gds.get("centrality_mechanisms", {})
    if centrality.get("success"):
        insights["bridge_mechanisms"] = [
            {"mechanism": r["mechanism"], "betweenness": r["betweenness"]}
            for r in centrality.get("data", [])[:10]
        ]
    
    # Similar archetypes
    similarity = gds.get("similarity_archetypes", {})
    if similarity.get("success"):
        insights["similar_archetypes"] = [
            {"archetype1": r["archetype1"], "archetype2": r["archetype2"], "similarity": r["similarity"]}
            for r in similarity.get("data", []) if r["similarity"] > 0.5
        ]
    
    # Extract from simple queries
    simple = results.get("simple_queries", {})
    
    # Top mechanisms by template votes
    top_mechs = simple.get("top_mechanisms_by_templates", {})
    if top_mechs.get("success") and not insights["influential_mechanisms"]:
        insights["influential_mechanisms"] = [
            {"mechanism": r["mechanism"], "template_count": r["template_count"], "total_votes": r["total_votes"]}
            for r in top_mechs.get("data", [])[:10]
        ]
    
    return insights


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Activate Graph Algorithms")
    parser.add_argument("--algorithm", type=str, help="Run specific algorithm")
    parser.add_argument("--no-gds", action="store_true", help="Skip GDS algorithms")
    parser.add_argument("--output", type=str, default="data/graph_algorithm_results.json")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("ACTIVATE GRAPH ALGORITHMS")
    print("=" * 70)
    
    runner = GraphAlgorithmRunner()
    
    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    await runner.connect()
    
    if args.algorithm:
        # Run specific algorithm
        if args.algorithm in ALGORITHM_QUERIES:
            result = await runner.run_gds_algorithm(
                args.algorithm,
                ALGORITHM_QUERIES[args.algorithm]
            )
            print(json.dumps(result, indent=2, default=str))
        elif args.algorithm in SIMPLE_QUERIES:
            result = await runner.run_simple_query(
                args.algorithm,
                SIMPLE_QUERIES[args.algorithm]
            )
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Unknown algorithm: {args.algorithm}")
            print(f"Available GDS: {list(ALGORITHM_QUERIES.keys())}")
            print(f"Available simple: {list(SIMPLE_QUERIES.keys())}")
    else:
        # Run all algorithms
        results = await runner.run_all_algorithms(include_gds=not args.no_gds)
        
        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        runner.save_results(output_path)
        
        # Extract insights
        insights = extract_intelligence_insights(results)
        
        # Save insights
        insights_path = Path("data/graph_intelligence_insights.json")
        with open(insights_path, "w") as f:
            json.dump(insights, f, indent=2)
        logger.info(f"Insights saved to: {insights_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("ALGORITHM RESULTS SUMMARY")
        print("=" * 70)
        
        gds_success = sum(1 for r in results.get("gds_algorithms", {}).values() if r.get("success"))
        gds_total = len(results.get("gds_algorithms", {}))
        simple_success = sum(1 for r in results.get("simple_queries", {}).values() if r.get("success"))
        simple_total = len(results.get("simple_queries", {}))
        
        print(f"GDS Algorithms: {gds_success}/{gds_total} successful")
        print(f"Simple Queries: {simple_success}/{simple_total} successful")
        
        if insights["influential_mechanisms"]:
            print(f"\nTop Influential Mechanisms:")
            for m in insights["influential_mechanisms"][:5]:
                print(f"  - {m.get('mechanism')}: {m.get('influence_score', m.get('total_votes', 'N/A'))}")
        
        if insights["archetype_clusters"]:
            print(f"\nArchetype Clusters Found: {len(insights['archetype_clusters'])}")
            for c in insights["archetype_clusters"][:3]:
                print(f"  - Cluster {c['cluster_id']}: {c['archetypes']}")
        
        if insights["bridge_mechanisms"]:
            print(f"\nBridge Mechanisms (connect archetypes):")
            for m in insights["bridge_mechanisms"][:5]:
                print(f"  - {m['mechanism']}: betweenness={m['betweenness']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
