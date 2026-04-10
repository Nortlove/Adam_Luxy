"""
Bulk Neo4j writer using UNWIND for batch operations.

All writes use parameterized UNWIND queries for performance.
Typical throughput: 5,000-10,000 nodes/second, 10,000-50,000 edges/second.
"""

from __future__ import annotations

import time
from typing import Any

from neo4j import Driver


class BulkWriter:
    """Batched Neo4j writer using UNWIND."""

    def __init__(self, driver: Driver, batch_size: int = 500):
        self.driver = driver
        self.batch_size = batch_size
        self._stats = {"nodes_written": 0, "edges_written": 0, "elapsed_s": 0.0}

    @property
    def stats(self) -> dict[str, Any]:
        return self._stats.copy()

    # =========================================================================
    # PRODUCT DESCRIPTION NODES
    # =========================================================================

    def write_product_descriptions(self, records: list[dict[str, Any]]) -> int:
        """Write ProductDescription nodes in batches."""
        query = """
        UNWIND $batch AS row
        MERGE (pd:ProductDescription {asin: row.asin})
        SET pd += row.properties
        """
        return self._write_batched(query, records, "nodes")

    # =========================================================================
    # ANNOTATED REVIEW NODES
    # =========================================================================

    def write_annotated_reviews(self, records: list[dict[str, Any]]) -> int:
        """Write AnnotatedReview nodes in batches."""
        query = """
        UNWIND $batch AS row
        MERGE (r:AnnotatedReview {review_id: row.review_id})
        SET r += row.properties
        """
        return self._write_batched(query, records, "nodes")

    # =========================================================================
    # REVIEWER NODES
    # =========================================================================

    def write_reviewers(self, records: list[dict[str, Any]]) -> int:
        """Write/update Reviewer nodes."""
        query = """
        UNWIND $batch AS row
        MERGE (rv:Reviewer {reviewer_id: row.reviewer_id})
        SET rv.review_count = coalesce(rv.review_count, 0) + 1
        """
        return self._write_batched(query, records, "nodes")

    # =========================================================================
    # PRODUCT ECOSYSTEM NODES
    # =========================================================================

    def write_ecosystems(self, records: list[dict[str, Any]]) -> int:
        """Write ProductEcosystem nodes."""
        query = """
        UNWIND $batch AS row
        MERGE (eco:ProductEcosystem {asin: row.asin})
        SET eco += row.properties
        """
        return self._write_batched(query, records, "nodes")

    # =========================================================================
    # EDGE TYPE 1: BRAND_CONVERTED
    # =========================================================================

    def write_brand_converted_edges(self, records: list[dict[str, Any]]) -> int:
        """Write BRAND_CONVERTED edges (ProductDescription -> AnnotatedReview)."""
        query = """
        UNWIND $batch AS row
        MATCH (pd:ProductDescription {asin: row.product_asin})
        MATCH (r:AnnotatedReview {review_id: row.review_id})
        MERGE (pd)-[e:BRAND_CONVERTED]->(r)
        SET e += row.properties
        """
        return self._write_batched(query, records, "edges")

    # =========================================================================
    # EDGE TYPE 2: PEER_INFLUENCED
    # =========================================================================

    def write_peer_influenced_edges(self, records: list[dict[str, Any]]) -> int:
        """Write PEER_INFLUENCED edges (peer Review -> buyer Review)."""
        query = """
        UNWIND $batch AS row
        MATCH (peer:AnnotatedReview {review_id: row.peer_review_id})
        MATCH (buyer:AnnotatedReview {review_id: row.buyer_review_id})
        MERGE (peer)-[e:PEER_INFLUENCED]->(buyer)
        SET e += row.properties
        """
        return self._write_batched(query, records, "edges")

    # =========================================================================
    # EDGE TYPE 3: ECOSYSTEM_CONVERTED
    # =========================================================================

    def write_ecosystem_converted_edges(self, records: list[dict[str, Any]]) -> int:
        """Write ECOSYSTEM_CONVERTED edges (ProductEcosystem -> AnnotatedReview)."""
        query = """
        UNWIND $batch AS row
        MATCH (eco:ProductEcosystem {asin: row.product_asin})
        MATCH (r:AnnotatedReview {review_id: row.review_id})
        MERGE (eco)-[e:ECOSYSTEM_CONVERTED]->(r)
        SET e += row.properties
        """
        return self._write_batched(query, records, "edges")

    # =========================================================================
    # SUPPORTING EDGES
    # =========================================================================

    def write_authored_edges(self, records: list[dict[str, Any]]) -> int:
        """Write AUTHORED edges (Reviewer -> AnnotatedReview)."""
        query = """
        UNWIND $batch AS row
        MATCH (rv:Reviewer {reviewer_id: row.reviewer_id})
        MATCH (r:AnnotatedReview {review_id: row.review_id})
        MERGE (rv)-[:AUTHORED]->(r)
        """
        return self._write_batched(query, records, "edges")

    def write_has_review_edges(self, records: list[dict[str, Any]]) -> int:
        """Write HAS_REVIEW edges (ProductDescription -> AnnotatedReview)."""
        query = """
        UNWIND $batch AS row
        MATCH (pd:ProductDescription {asin: row.product_asin})
        MATCH (r:AnnotatedReview {review_id: row.review_id})
        MERGE (pd)-[:HAS_REVIEW]->(r)
        """
        return self._write_batched(query, records, "edges")

    def write_anchors_edges(self, records: list[dict[str, Any]]) -> int:
        """Write ANCHORS edges (ProductDescription -> ProductEcosystem)."""
        query = """
        UNWIND $batch AS row
        MATCH (pd:ProductDescription {asin: row.asin})
        MATCH (eco:ProductEcosystem {asin: row.asin})
        MERGE (pd)-[:ANCHORS]->(eco)
        """
        return self._write_batched(query, records, "edges")

    # =========================================================================
    # INTERNAL
    # =========================================================================

    def _write_batched(
        self, query: str, records: list[dict[str, Any]], count_type: str
    ) -> int:
        """Execute a query in batches using UNWIND."""
        t0 = time.time()
        total = 0
        with self.driver.session() as session:
            for i in range(0, len(records), self.batch_size):
                batch = records[i : i + self.batch_size]
                session.run(query, batch=batch)
                total += len(batch)
        elapsed = time.time() - t0
        self._stats[f"{count_type}_written"] += total
        self._stats["elapsed_s"] += elapsed
        return total
