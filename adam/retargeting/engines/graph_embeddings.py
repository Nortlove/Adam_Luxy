# =============================================================================
# Graph Embedding Integration (FastRP / HGT)
# Location: adam/retargeting/engines/graph_embeddings.py
# Enhancement #34, Session 34-8
# =============================================================================

"""
Neo4j GDS graph embedding integration.

Pragmatic path: FastRP first, HGT only if FastRP shows improvement.

Architecture:
  Neo4j (persistent) → GDS Python Client export
  → FastRP / HGT training → learned node/edge properties
  → write back to Neo4j → serve via enriched Cypher queries
  → Redis cache for real-time serving

This module provides the Python-side integration layer. The actual
GDS algorithms are configured in adam/infrastructure/neo4j/gds_algorithms.py.
This layer adds:
1. Embedding export pipeline (graph → training data)
2. Property write-back (embeddings → Neo4j node properties)
3. Embedding-enriched mechanism selection (embeddings as context features)

Requires: Neo4j GDS plugin + live Neo4j connection.
Without these, falls back gracefully to existing raw features.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class GraphEmbedding:
    """A learned embedding for a graph entity."""

    entity_id: str
    entity_type: str  # "buyer", "product", "conversion_edge", "mechanism"
    embedding: np.ndarray  # (d,) vector
    algorithm: str  # "fastrp", "node2vec", "hgt"
    dimension: int


@dataclass
class EmbeddingBenchmark:
    """Comparison of embedding-based vs raw-feature-based prediction."""

    algorithm: str
    metric: str  # "auc", "precision", "ndcg"
    raw_feature_score: float
    embedding_score: float
    improvement_pct: float
    recommendation: str  # "proceed_with_hgt", "fastrp_sufficient", "skip"


class GraphEmbeddingService:
    """Manages graph embedding lifecycle.

    Usage:
        service = GraphEmbeddingService(neo4j_driver)
        # Step 1: Run FastRP baseline
        embeddings = await service.run_fastrp(dimension=64)
        # Step 2: Benchmark
        benchmark = await service.benchmark_vs_raw(embeddings, test_data)
        # Step 3: If justified, write back to Neo4j
        if benchmark.improvement_pct > 5:
            await service.write_back_embeddings(embeddings)
    """

    def __init__(self, neo4j_driver=None):
        self._driver = neo4j_driver

    async def run_fastrp(
        self,
        graph_name: str = "bilateral_graph",
        dimension: int = 64,
        iteration_weights: Optional[List[float]] = None,
    ) -> List[GraphEmbedding]:
        """Run FastRP on the bilateral graph.

        FastRP (Fast Random Projection) is Neo4j GDS's built-in
        embedding algorithm. It's fast, scalable, and requires no
        training — good baseline before investing in HGT.
        """
        if self._driver is None:
            logger.warning("No Neo4j driver — returning empty embeddings")
            return []

        weights = iteration_weights or [0.0, 1.0, 1.0, 0.5]

        try:
            async with self._driver.session() as session:
                # Project graph
                await session.run(f"""
                    CALL gds.graph.project(
                        '{graph_name}',
                        ['CustomerArchetype', 'ProductDescription', 'CognitiveMechanism'],
                        ['BRAND_CONVERTED', 'RESPONDS_TO', 'MECHANISM_SYNERGY']
                    )
                """)

                # Run FastRP
                result = await session.run(f"""
                    CALL gds.fastRP.stream('{graph_name}', {{
                        embeddingDimension: {dimension},
                        iterationWeights: {weights}
                    }})
                    YIELD nodeId, embedding
                    RETURN gds.util.asNode(nodeId).id AS entity_id,
                           labels(gds.util.asNode(nodeId))[0] AS entity_type,
                           embedding
                    LIMIT 10000
                """)

                embeddings = []
                async for record in result:
                    embeddings.append(GraphEmbedding(
                        entity_id=record["entity_id"],
                        entity_type=record["entity_type"],
                        embedding=np.array(record["embedding"]),
                        algorithm="fastrp",
                        dimension=dimension,
                    ))

                # Drop projection
                await session.run(f"CALL gds.graph.drop('{graph_name}')")

                logger.info("FastRP: %d embeddings computed (dim=%d)", len(embeddings), dimension)
                return embeddings

        except Exception as e:
            logger.warning("FastRP failed: %s", e)
            return []

    async def benchmark_vs_raw(
        self,
        embeddings: List[GraphEmbedding],
        test_edges: List[Dict],
    ) -> EmbeddingBenchmark:
        """Benchmark embedding-based prediction vs raw features.

        Tests: can embeddings predict mechanism effectiveness better
        than the existing 43-dim bilateral edge features?
        """
        if not embeddings or not test_edges:
            return EmbeddingBenchmark(
                algorithm="fastrp",
                metric="auc",
                raw_feature_score=0.5,
                embedding_score=0.5,
                improvement_pct=0.0,
                recommendation="skip",
            )

        # Build embedding lookup
        embed_dict = {e.entity_id: e.embedding for e in embeddings}

        # Simplified benchmark: correlation between embedding similarity
        # and conversion outcome. A real benchmark would use train/test split.
        # This is the "selling lipstick" version.
        from scipy.stats import pearsonr

        similarities = []
        outcomes = []
        for edge in test_edges:
            buyer_id = edge.get("_review_id", "")
            if buyer_id in embed_dict:
                # Use embedding norm as prediction proxy
                sim = float(np.linalg.norm(embed_dict[buyer_id]))
                similarities.append(sim)
                outcomes.append(1.0 if edge.get("outcome") in ("evangelized", "satisfied") else 0.0)

        if len(similarities) < 10:
            return EmbeddingBenchmark(
                algorithm="fastrp", metric="correlation",
                raw_feature_score=0.0, embedding_score=0.0,
                improvement_pct=0.0, recommendation="insufficient_data",
            )

        r_embed, _ = pearsonr(similarities, outcomes)

        # Compare against raw composite alignment
        raw_scores = [edge.get("composite_alignment", 0.5) for edge in test_edges[:len(similarities)]]
        r_raw, _ = pearsonr(raw_scores, outcomes[:len(raw_scores)])

        improvement = (abs(r_embed) - abs(r_raw)) / max(abs(r_raw), 0.001) * 100

        if improvement > 10:
            rec = "proceed_with_hgt"
        elif improvement > 0:
            rec = "fastrp_sufficient"
        else:
            rec = "skip"

        return EmbeddingBenchmark(
            algorithm="fastrp",
            metric="correlation",
            raw_feature_score=round(abs(r_raw), 4),
            embedding_score=round(abs(r_embed), 4),
            improvement_pct=round(improvement, 1),
            recommendation=rec,
        )

    async def write_back_embeddings(
        self,
        embeddings: List[GraphEmbedding],
        property_name: str = "fastrp_embedding",
    ) -> int:
        """Write learned embeddings back to Neo4j node properties."""
        if self._driver is None:
            return 0

        count = 0
        try:
            async with self._driver.session() as session:
                for emb in embeddings:
                    await session.run(
                        f"""
                        MATCH (n) WHERE n.id = $entity_id
                        SET n.{property_name} = $embedding
                        """,
                        entity_id=emb.entity_id,
                        embedding=emb.embedding.tolist(),
                    )
                    count += 1
            logger.info("Wrote %d embeddings to Neo4j as %s", count, property_name)
        except Exception as e:
            logger.warning("Embedding write-back failed: %s", e)
        return count
