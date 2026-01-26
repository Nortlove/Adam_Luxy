# =============================================================================
# ADAM pgvector Backend
# Location: adam/embeddings/pgvector.py
# =============================================================================

"""
PGVECTOR BACKEND

Production-grade PostgreSQL vector storage using pgvector extension.

Features:
- Persistent vector storage with ACID guarantees
- Multiple index types (IVFFlat, HNSW)
- Efficient similarity search with pre-filtering
- Connection pooling
- Automatic schema migration
- Prometheus metrics
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from prometheus_client import Counter, Histogram, Gauge

from adam.embeddings.models import (
    EmbeddingVector,
    EmbeddingType,
    EmbeddingNamespace,
    SimilarityMetric,
    SearchFilter,
    SearchMatch,
    IndexConfig,
    IndexType,
)
from adam.embeddings.store import VectorStoreBackend
from adam.config.settings import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

PGVECTOR_OPERATIONS = Counter(
    "adam_pgvector_operations_total",
    "pgvector operations",
    ["operation", "status"],
)

PGVECTOR_LATENCY = Histogram(
    "adam_pgvector_latency_seconds",
    "pgvector operation latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

PGVECTOR_POOL_SIZE = Gauge(
    "adam_pgvector_pool_size",
    "pgvector connection pool size",
)

PGVECTOR_VECTOR_COUNT = Gauge(
    "adam_pgvector_vector_count",
    "Number of vectors in pgvector",
    ["namespace", "embedding_type"],
)


# =============================================================================
# SQL TEMPLATES
# =============================================================================

SQL_CREATE_EXTENSION = "CREATE EXTENSION IF NOT EXISTS vector;"

SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS adam_embeddings (
    id SERIAL PRIMARY KEY,
    vector_id VARCHAR(64) UNIQUE NOT NULL,
    namespace VARCHAR(32) NOT NULL,
    embedding_type VARCHAR(64) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    source_text TEXT,
    source_hash VARCHAR(32),
    model VARCHAR(64) NOT NULL,
    model_version VARCHAR(16) DEFAULT '1.0',
    vector vector({dimensions}),
    dimensions INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    generation_latency_ms FLOAT,
    token_count INTEGER
);
"""

SQL_CREATE_INDEXES = """
-- Unique index on vector_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_vector_id 
ON adam_embeddings(vector_id);

-- Index on source_id for lookups
CREATE INDEX IF NOT EXISTS idx_embeddings_source_id 
ON adam_embeddings(source_id);

-- Composite index for namespace + type filtering
CREATE INDEX IF NOT EXISTS idx_embeddings_namespace_type 
ON adam_embeddings(namespace, embedding_type);

-- Index on tags using GIN
CREATE INDEX IF NOT EXISTS idx_embeddings_tags 
ON adam_embeddings USING GIN(tags);

-- Index on metadata using GIN
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata 
ON adam_embeddings USING GIN(metadata);

-- Index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_embeddings_created_at 
ON adam_embeddings(created_at);
"""

SQL_CREATE_HNSW_INDEX = """
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw_{namespace}
ON adam_embeddings 
USING hnsw (vector vector_cosine_ops)
WHERE namespace = '{namespace}'
WITH (m = {m}, ef_construction = {ef_construction});
"""

SQL_CREATE_IVFFLAT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivf_{namespace}
ON adam_embeddings 
USING ivfflat (vector vector_cosine_ops)
WHERE namespace = '{namespace}'
WITH (lists = {nlist});
"""

SQL_INSERT_VECTOR = """
INSERT INTO adam_embeddings (
    vector_id, namespace, embedding_type, source_id, source_text,
    source_hash, model, model_version, vector, dimensions,
    metadata, tags, created_at, generation_latency_ms, token_count
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
)
ON CONFLICT (vector_id) DO UPDATE SET
    vector = EXCLUDED.vector,
    metadata = EXCLUDED.metadata,
    tags = EXCLUDED.tags,
    updated_at = NOW(),
    version = adam_embeddings.version + 1
RETURNING id;
"""

SQL_GET_VECTOR = """
SELECT 
    vector_id, namespace, embedding_type, source_id, source_text,
    source_hash, model, model_version, vector, dimensions,
    metadata, tags, created_at, updated_at, version,
    generation_latency_ms, token_count
FROM adam_embeddings
WHERE vector_id = $1;
"""

SQL_DELETE_VECTOR = """
DELETE FROM adam_embeddings WHERE vector_id = $1 RETURNING id;
"""

SQL_SEARCH_COSINE = """
SELECT 
    vector_id, source_id, namespace, embedding_type, metadata, source_text,
    1 - (vector <=> $1::vector) AS similarity
FROM adam_embeddings
WHERE namespace = $2
{type_filter}
{metadata_filter}
{tag_filter}
{time_filter}
ORDER BY vector <=> $1::vector
LIMIT $3;
"""

SQL_SEARCH_EUCLIDEAN = """
SELECT 
    vector_id, source_id, namespace, embedding_type, metadata, source_text,
    vector <-> $1::vector AS distance
FROM adam_embeddings
WHERE namespace = $2
{type_filter}
{metadata_filter}
{tag_filter}
{time_filter}
ORDER BY vector <-> $1::vector
LIMIT $3;
"""

SQL_SEARCH_DOT_PRODUCT = """
SELECT 
    vector_id, source_id, namespace, embedding_type, metadata, source_text,
    (vector <#> $1::vector) * -1 AS similarity
FROM adam_embeddings
WHERE namespace = $2
{type_filter}
{metadata_filter}
{tag_filter}
{time_filter}
ORDER BY vector <#> $1::vector
LIMIT $3;
"""

SQL_COUNT = """
SELECT COUNT(*) FROM adam_embeddings
WHERE 1=1
{namespace_filter}
{type_filter};
"""


# =============================================================================
# PGVECTOR BACKEND
# =============================================================================

class PgVectorBackend(VectorStoreBackend):
    """
    PostgreSQL pgvector backend for production vector storage.
    
    Requires:
    - PostgreSQL 14+ with pgvector extension
    - asyncpg library
    
    Usage:
        backend = PgVectorBackend(
            connection_string="postgresql://user:pass@localhost/adam",
            dimensions=384,
        )
        await backend.initialize()
        await backend.store(vector)
        results = await backend.search(query_vector, namespace, top_k=10)
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        dimensions: int = 384,
        pool_min_size: int = 5,
        pool_max_size: int = 20,
        index_type: IndexType = IndexType.HNSW,
        hnsw_m: int = 16,
        hnsw_ef_construction: int = 64,
        ivf_nlist: int = 100,
    ):
        """
        Initialize pgvector backend.
        
        Args:
            connection_string: PostgreSQL connection string
            dimensions: Vector dimensions
            pool_min_size: Minimum connection pool size
            pool_max_size: Maximum connection pool size
            index_type: Type of vector index (HNSW or IVF)
            hnsw_m: HNSW M parameter (connections per layer)
            hnsw_ef_construction: HNSW construction search depth
            ivf_nlist: IVF number of clusters
        """
        settings = get_settings()
        
        self._connection_string = connection_string or settings.neo4j.uri.replace(
            "bolt://", "postgresql://"
        )  # Fallback, should be configured
        self._dimensions = dimensions
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._index_type = index_type
        self._hnsw_m = hnsw_m
        self._hnsw_ef_construction = hnsw_ef_construction
        self._ivf_nlist = ivf_nlist
        
        self._pool = None
        self._initialized = False
        self._namespace_indexes: Dict[str, bool] = {}
    
    @property
    def backend_name(self) -> str:
        return "pgvector"
    
    async def initialize(self) -> None:
        """Initialize connection pool and schema."""
        if self._initialized:
            return
        
        try:
            import asyncpg
            
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=self._pool_min_size,
                max_size=self._pool_max_size,
            )
            
            PGVECTOR_POOL_SIZE.set(self._pool_max_size)
            
            # Initialize schema
            await self._initialize_schema()
            
            self._initialized = True
            logger.info("pgvector backend initialized successfully")
            
        except ImportError:
            raise RuntimeError(
                "asyncpg not installed. Run: pip install asyncpg"
            )
        except Exception as e:
            logger.error(f"Failed to initialize pgvector: {e}")
            raise
    
    async def _initialize_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with self._pool.acquire() as conn:
            # Create extension
            await conn.execute(SQL_CREATE_EXTENSION)
            
            # Create table
            create_table = SQL_CREATE_TABLE.format(dimensions=self._dimensions)
            await conn.execute(create_table)
            
            # Create indexes
            await conn.execute(SQL_CREATE_INDEXES)
            
            logger.info("pgvector schema initialized")
    
    async def _ensure_vector_index(self, namespace: str) -> None:
        """Ensure vector index exists for namespace."""
        if namespace in self._namespace_indexes:
            return
        
        async with self._pool.acquire() as conn:
            try:
                if self._index_type == IndexType.HNSW:
                    sql = SQL_CREATE_HNSW_INDEX.format(
                        namespace=namespace,
                        m=self._hnsw_m,
                        ef_construction=self._hnsw_ef_construction,
                    )
                else:
                    sql = SQL_CREATE_IVFFLAT_INDEX.format(
                        namespace=namespace,
                        nlist=self._ivf_nlist,
                    )
                
                await conn.execute(sql)
                self._namespace_indexes[namespace] = True
                logger.info(f"Created {self._index_type.value} index for namespace {namespace}")
                
            except Exception as e:
                # Index might already exist
                logger.debug(f"Index creation note: {e}")
                self._namespace_indexes[namespace] = True
    
    async def store(self, vector: EmbeddingVector) -> None:
        """Store a vector in PostgreSQL."""
        if not self._initialized:
            await self.initialize()
        
        start = time.perf_counter()
        
        try:
            # Ensure index exists for namespace
            await self._ensure_vector_index(vector.namespace.value)
            
            async with self._pool.acquire() as conn:
                # Format vector for pgvector
                vector_str = "[" + ",".join(str(v) for v in vector.vector) + "]"
                
                await conn.execute(
                    SQL_INSERT_VECTOR,
                    vector.vector_id,
                    vector.namespace.value,
                    vector.embedding_type.value,
                    vector.source_id,
                    vector.source_text,
                    vector.source_hash,
                    vector.model.value,
                    vector.model_version,
                    vector_str,
                    vector.dimensions,
                    json.dumps(vector.metadata),
                    vector.tags,
                    vector.created_at,
                    vector.generation_latency_ms,
                    vector.token_count,
                )
            
            PGVECTOR_OPERATIONS.labels(operation="store", status="success").inc()
            PGVECTOR_VECTOR_COUNT.labels(
                namespace=vector.namespace.value,
                embedding_type=vector.embedding_type.value,
            ).inc()
            
        except Exception as e:
            PGVECTOR_OPERATIONS.labels(operation="store", status="error").inc()
            logger.error(f"Failed to store vector: {e}")
            raise
        
        finally:
            duration = time.perf_counter() - start
            PGVECTOR_LATENCY.labels(operation="store").observe(duration)
    
    async def store_batch(self, vectors: List[EmbeddingVector]) -> int:
        """Store batch of vectors."""
        if not self._initialized:
            await self.initialize()
        
        start = time.perf_counter()
        stored = 0
        
        try:
            # Group by namespace for index creation
            namespaces = set(v.namespace.value for v in vectors)
            for ns in namespaces:
                await self._ensure_vector_index(ns)
            
            async with self._pool.acquire() as conn:
                # Use batch insert
                for vector in vectors:
                    try:
                        vector_str = "[" + ",".join(str(v) for v in vector.vector) + "]"
                        
                        await conn.execute(
                            SQL_INSERT_VECTOR,
                            vector.vector_id,
                            vector.namespace.value,
                            vector.embedding_type.value,
                            vector.source_id,
                            vector.source_text,
                            vector.source_hash,
                            vector.model.value,
                            vector.model_version,
                            vector_str,
                            vector.dimensions,
                            json.dumps(vector.metadata),
                            vector.tags,
                            vector.created_at,
                            vector.generation_latency_ms,
                            vector.token_count,
                        )
                        stored += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to store vector {vector.vector_id}: {e}")
            
            PGVECTOR_OPERATIONS.labels(operation="store_batch", status="success").inc()
            
        except Exception as e:
            PGVECTOR_OPERATIONS.labels(operation="store_batch", status="error").inc()
            logger.error(f"Batch store failed: {e}")
            raise
        
        finally:
            duration = time.perf_counter() - start
            PGVECTOR_LATENCY.labels(operation="store_batch").observe(duration)
        
        return stored
    
    async def get(self, vector_id: str) -> Optional[EmbeddingVector]:
        """Retrieve a vector by ID."""
        if not self._initialized:
            await self.initialize()
        
        start = time.perf_counter()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(SQL_GET_VECTOR, vector_id)
                
                if not row:
                    return None
                
                return self._row_to_vector(row)
                
        except Exception as e:
            PGVECTOR_OPERATIONS.labels(operation="get", status="error").inc()
            logger.error(f"Failed to get vector: {e}")
            return None
        
        finally:
            duration = time.perf_counter() - start
            PGVECTOR_LATENCY.labels(operation="get").observe(duration)
    
    async def delete(self, vector_id: str) -> bool:
        """Delete a vector by ID."""
        if not self._initialized:
            await self.initialize()
        
        start = time.perf_counter()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(SQL_DELETE_VECTOR, vector_id)
                deleted = result == "DELETE 1"
                
                if deleted:
                    PGVECTOR_OPERATIONS.labels(operation="delete", status="success").inc()
                else:
                    PGVECTOR_OPERATIONS.labels(operation="delete", status="not_found").inc()
                
                return deleted
                
        except Exception as e:
            PGVECTOR_OPERATIONS.labels(operation="delete", status="error").inc()
            logger.error(f"Failed to delete vector: {e}")
            return False
        
        finally:
            duration = time.perf_counter() - start
            PGVECTOR_LATENCY.labels(operation="delete").observe(duration)
    
    async def search(
        self,
        query_vector: List[float],
        namespace: EmbeddingNamespace,
        embedding_type: Optional[EmbeddingType] = None,
        top_k: int = 10,
        filter: Optional[SearchFilter] = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> List[SearchMatch]:
        """Search for similar vectors."""
        if not self._initialized:
            await self.initialize()
        
        start = time.perf_counter()
        
        try:
            # Build filter clauses
            type_filter = ""
            if embedding_type:
                type_filter = f"AND embedding_type = '{embedding_type.value}'"
            elif filter and filter.embedding_types:
                types = ",".join(f"'{t.value}'" for t in filter.embedding_types)
                type_filter = f"AND embedding_type IN ({types})"
            
            metadata_filter = ""
            if filter and filter.metadata_equals:
                conditions = []
                for key, value in filter.metadata_equals.items():
                    if isinstance(value, str):
                        conditions.append(f"metadata->>'{key}' = '{value}'")
                    else:
                        conditions.append(f"metadata->>'{key}' = '{json.dumps(value)}'")
                if conditions:
                    metadata_filter = "AND " + " AND ".join(conditions)
            
            tag_filter = ""
            if filter:
                if filter.tags_any:
                    tags = ",".join(f"'{t}'" for t in filter.tags_any)
                    tag_filter = f"AND tags && ARRAY[{tags}]::text[]"
                elif filter.tags_all:
                    tags = ",".join(f"'{t}'" for t in filter.tags_all)
                    tag_filter = f"AND tags @> ARRAY[{tags}]::text[]"
            
            time_filter = ""
            if filter:
                if filter.created_after:
                    time_filter += f"AND created_at >= '{filter.created_after.isoformat()}'"
                if filter.created_before:
                    time_filter += f"AND created_at <= '{filter.created_before.isoformat()}'"
            
            # Select search query based on metric
            if metric == SimilarityMetric.EUCLIDEAN:
                sql_template = SQL_SEARCH_EUCLIDEAN
            elif metric == SimilarityMetric.DOT_PRODUCT:
                sql_template = SQL_SEARCH_DOT_PRODUCT
            else:
                sql_template = SQL_SEARCH_COSINE
            
            sql = sql_template.format(
                type_filter=type_filter,
                metadata_filter=metadata_filter,
                tag_filter=tag_filter,
                time_filter=time_filter,
            )
            
            # Format query vector
            vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
            
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(sql, vector_str, namespace.value, top_k)
                
                results = []
                for row in rows:
                    score = row.get("similarity", 0.0) or row.get("distance", 0.0)
                    if metric == SimilarityMetric.EUCLIDEAN:
                        # Convert distance to similarity score
                        score = 1 / (1 + score)
                    
                    results.append(SearchMatch(
                        vector_id=row["vector_id"],
                        source_id=row["source_id"],
                        score=float(score),
                        distance=float(row["distance"]) if "distance" in row else None,
                        namespace=EmbeddingNamespace(row["namespace"]),
                        embedding_type=EmbeddingType(row["embedding_type"]),
                        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                        source_text=row["source_text"],
                    ))
                
                PGVECTOR_OPERATIONS.labels(operation="search", status="success").inc()
                return results
                
        except Exception as e:
            PGVECTOR_OPERATIONS.labels(operation="search", status="error").inc()
            logger.error(f"Search failed: {e}")
            return []
        
        finally:
            duration = time.perf_counter() - start
            PGVECTOR_LATENCY.labels(operation="search").observe(duration)
    
    async def count(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        embedding_type: Optional[EmbeddingType] = None,
    ) -> int:
        """Count vectors matching criteria."""
        if not self._initialized:
            await self.initialize()
        
        try:
            namespace_filter = ""
            if namespace:
                namespace_filter = f"AND namespace = '{namespace.value}'"
            
            type_filter = ""
            if embedding_type:
                type_filter = f"AND embedding_type = '{embedding_type.value}'"
            
            sql = SQL_COUNT.format(
                namespace_filter=namespace_filter,
                type_filter=type_filter,
            )
            
            async with self._pool.acquire() as conn:
                result = await conn.fetchval(sql)
                return result or 0
                
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0
    
    def _row_to_vector(self, row) -> EmbeddingVector:
        """Convert database row to EmbeddingVector."""
        from adam.embeddings.models import EmbeddingModel
        
        # Parse vector string to list
        vector_str = str(row["vector"])
        vector_list = [float(v) for v in vector_str.strip("[]").split(",")]
        
        return EmbeddingVector(
            vector_id=row["vector_id"],
            namespace=EmbeddingNamespace(row["namespace"]),
            embedding_type=EmbeddingType(row["embedding_type"]),
            vector=vector_list,
            dimensions=row["dimensions"],
            source_id=row["source_id"],
            source_text=row["source_text"],
            source_hash=row["source_hash"],
            model=EmbeddingModel(row["model"]),
            model_version=row["model_version"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            tags=list(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            generation_latency_ms=row["generation_latency_ms"],
            token_count=row["token_count"],
        )
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._initialized = False
            logger.info("pgvector connection pool closed")
    
    # =========================================================================
    # ADMINISTRATIVE METHODS
    # =========================================================================
    
    async def vacuum_analyze(self) -> None:
        """Run VACUUM ANALYZE on embeddings table."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            await conn.execute("VACUUM ANALYZE adam_embeddings")
            logger.info("VACUUM ANALYZE completed on adam_embeddings")
    
    async def reindex(self, namespace: Optional[str] = None) -> None:
        """Reindex vector indexes."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            if namespace:
                index_name = f"idx_embeddings_vector_hnsw_{namespace}"
                await conn.execute(f"REINDEX INDEX CONCURRENTLY {index_name}")
                logger.info(f"Reindexed {index_name}")
            else:
                await conn.execute("REINDEX TABLE CONCURRENTLY adam_embeddings")
                logger.info("Reindexed all indexes on adam_embeddings")
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self._initialized:
            await self.initialize()
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    indexrelname as index_name,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                WHERE relname = 'adam_embeddings'
            """)
            
            return [dict(row) for row in rows]
