"""
Neo4j schema extension for the corpus annotation pipeline.

Adds the node types, edge types, indexes, and constraints required by the
8-phase annotation pipeline ON TOP of the existing construct taxonomy schema.
"""

from __future__ import annotations

from neo4j import Driver


SCHEMA_STATEMENTS: list[str] = [
    # =========================================================================
    # CONSTRAINTS — uniqueness
    # =========================================================================
    "CREATE CONSTRAINT product_desc_asin_unique IF NOT EXISTS "
    "FOR (pd:ProductDescription) REQUIRE pd.asin IS UNIQUE",

    "CREATE CONSTRAINT annotated_review_id_unique IF NOT EXISTS "
    "FOR (r:AnnotatedReview) REQUIRE r.review_id IS UNIQUE",

    "CREATE CONSTRAINT reviewer_id_unique IF NOT EXISTS "
    "FOR (rv:Reviewer) REQUIRE rv.reviewer_id IS UNIQUE",

    "CREATE CONSTRAINT ecosystem_asin_unique IF NOT EXISTS "
    "FOR (eco:ProductEcosystem) REQUIRE eco.asin IS UNIQUE",

    # =========================================================================
    # INDEXES — edge performance
    # =========================================================================
    "CREATE INDEX brand_buyer_outcome IF NOT EXISTS "
    "FOR ()-[e:BRAND_CONVERTED]-() ON (e.outcome)",

    "CREATE INDEX brand_buyer_category IF NOT EXISTS "
    "FOR ()-[e:BRAND_CONVERTED]-() ON (e.product_category)",

    "CREATE INDEX peer_buyer_influence IF NOT EXISTS "
    "FOR ()-[e:PEER_INFLUENCED]-() ON (e.influence_weight)",

    "CREATE INDEX eco_buyer_coherence IF NOT EXISTS "
    "FOR ()-[e:ECOSYSTEM_CONVERTED]-() ON (e.frame_coherence_at_time)",

    # =========================================================================
    # INDEXES — node lookup
    # =========================================================================
    "CREATE INDEX review_asin_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.asin)",

    "CREATE INDEX review_parent_asin_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.parent_asin)",

    "CREATE INDEX review_helpful_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.helpful_votes)",

    "CREATE INDEX review_rating_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.star_rating)",

    "CREATE INDEX review_timestamp_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.timestamp)",

    "CREATE INDEX review_user_idx IF NOT EXISTS "
    "FOR (r:AnnotatedReview) ON (r.user_id)",

    "CREATE INDEX pd_category_idx IF NOT EXISTS "
    "FOR (pd:ProductDescription) ON (pd.main_category)",

    "CREATE INDEX pd_parent_asin_idx IF NOT EXISTS "
    "FOR (pd:ProductDescription) ON (pd.parent_asin)",
]


def apply_schema(driver: Driver) -> int:
    """Apply all schema statements. Returns count of statements executed."""
    executed = 0
    with driver.session() as session:
        for stmt in SCHEMA_STATEMENTS:
            try:
                session.run(stmt)
                executed += 1
            except Exception as e:
                # Constraints/indexes that already exist will error — safe to skip
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    executed += 1
                else:
                    print(f"  WARN: {e}")
    return executed


def verify_schema(driver: Driver) -> dict[str, int]:
    """Verify schema was applied correctly."""
    with driver.session() as session:
        constraints = session.run(
            "SHOW CONSTRAINTS YIELD name RETURN count(name) AS cnt"
        ).single()["cnt"]
        indexes = session.run(
            "SHOW INDEXES YIELD name RETURN count(name) AS cnt"
        ).single()["cnt"]
        labels = session.run(
            "CALL db.labels() YIELD label RETURN collect(label) AS labels"
        ).single()["labels"]
    return {
        "constraints": constraints,
        "indexes": indexes,
        "labels": labels,
    }
