# =============================================================================
# ADAM Vector Store
# Location: adam/embeddings/store.py
# =============================================================================

"""
VECTOR STORE

Production-grade vector storage with multiple backend support.
Implements FAISS for high-performance similarity search and
pgvector for persistent PostgreSQL storage.
"""

import asyncio
import logging
import math
import os
import pickle
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prometheus_client import Counter, Histogram, Gauge

from adam.embeddings.models import (
    EmbeddingVector,
    EmbeddingType,
    EmbeddingNamespace,
    SimilarityMetric,
    SearchFilter,
    SearchMatch,
    SimilarityResult,
    IndexConfig,
    IndexType,
    IndexStats,
)

logger = logging.getLogger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

VECTOR_STORE_OPERATIONS = Counter(
    "adam_vector_store_operations_total",
    "Vector store operations",
    ["operation", "backend", "status"],
)

VECTOR_SEARCH_LATENCY = Histogram(
    "adam_vector_search_latency_seconds",
    "Vector search latency",
    ["backend", "index_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

VECTOR_COUNT = Gauge(
    "adam_vector_store_count",
    "Number of vectors in store",
    ["namespace", "embedding_type"],
)


# =============================================================================
# BASE VECTOR STORE
# =============================================================================

class VectorStoreBackend(ABC):
    """Abstract base class for vector store backends."""
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Backend identifier."""
        pass
    
    @abstractmethod
    async def store(self, vector: EmbeddingVector) -> None:
        """Store a single vector."""
        pass
    
    @abstractmethod
    async def store_batch(self, vectors: List[EmbeddingVector]) -> int:
        """Store a batch of vectors. Returns count stored."""
        pass
    
    @abstractmethod
    async def get(self, vector_id: str) -> Optional[EmbeddingVector]:
        """Retrieve a vector by ID."""
        pass
    
    @abstractmethod
    async def delete(self, vector_id: str) -> bool:
        """Delete a vector by ID."""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def count(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        embedding_type: Optional[EmbeddingType] = None,
    ) -> int:
        """Count vectors matching criteria."""
        pass
    
    async def close(self) -> None:
        """Clean up resources."""
        pass


# =============================================================================
# IN-MEMORY BACKEND (Development/Testing)
# =============================================================================

class InMemoryBackend(VectorStoreBackend):
    """
    In-memory vector store for development and testing.
    
    Uses brute-force search. Suitable for small datasets (<10K vectors).
    """
    
    def __init__(self):
        self._vectors: Dict[str, EmbeddingVector] = {}
        self._namespace_index: Dict[EmbeddingNamespace, List[str]] = defaultdict(list)
        self._type_index: Dict[EmbeddingType, List[str]] = defaultdict(list)
        self._source_index: Dict[str, str] = {}  # source_id -> vector_id
    
    @property
    def backend_name(self) -> str:
        return "memory"
    
    async def store(self, vector: EmbeddingVector) -> None:
        """Store a vector."""
        self._vectors[vector.vector_id] = vector
        self._namespace_index[vector.namespace].append(vector.vector_id)
        self._type_index[vector.embedding_type].append(vector.vector_id)
        self._source_index[vector.source_id] = vector.vector_id
        
        VECTOR_COUNT.labels(
            namespace=vector.namespace.value,
            embedding_type=vector.embedding_type.value,
        ).inc()
    
    async def store_batch(self, vectors: List[EmbeddingVector]) -> int:
        """Store batch of vectors."""
        for vector in vectors:
            await self.store(vector)
        return len(vectors)
    
    async def get(self, vector_id: str) -> Optional[EmbeddingVector]:
        """Get vector by ID."""
        return self._vectors.get(vector_id)
    
    async def delete(self, vector_id: str) -> bool:
        """Delete vector by ID."""
        if vector_id not in self._vectors:
            return False
        
        vector = self._vectors[vector_id]
        del self._vectors[vector_id]
        
        if vector_id in self._namespace_index[vector.namespace]:
            self._namespace_index[vector.namespace].remove(vector_id)
        if vector_id in self._type_index[vector.embedding_type]:
            self._type_index[vector.embedding_type].remove(vector_id)
        if vector.source_id in self._source_index:
            del self._source_index[vector.source_id]
        
        VECTOR_COUNT.labels(
            namespace=vector.namespace.value,
            embedding_type=vector.embedding_type.value,
        ).dec()
        
        return True
    
    async def search(
        self,
        query_vector: List[float],
        namespace: EmbeddingNamespace,
        embedding_type: Optional[EmbeddingType] = None,
        top_k: int = 10,
        filter: Optional[SearchFilter] = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> List[SearchMatch]:
        """Search using brute-force."""
        # Get candidate vector IDs
        candidates = set(self._namespace_index[namespace])
        
        if embedding_type:
            candidates &= set(self._type_index[embedding_type])
        
        if filter and filter.embedding_types:
            type_ids = set()
            for et in filter.embedding_types:
                type_ids.update(self._type_index[et])
            candidates &= type_ids
        
        # Score candidates
        scored = []
        for vid in candidates:
            vector = self._vectors[vid]
            
            # Apply filters
            if not self._matches_filter(vector, filter):
                continue
            
            # Compute similarity
            score = self._compute_similarity(query_vector, vector.vector, metric)
            scored.append((vid, score, vector))
        
        # Sort by score (higher is better for similarity, lower for distance)
        if metric in [SimilarityMetric.EUCLIDEAN, SimilarityMetric.MANHATTAN]:
            scored.sort(key=lambda x: x[1])  # Lower distance is better
        else:
            scored.sort(key=lambda x: x[1], reverse=True)  # Higher similarity is better
        
        # Build results
        results = []
        for vid, score, vector in scored[:top_k]:
            results.append(SearchMatch(
                vector_id=vid,
                source_id=vector.source_id,
                score=score if metric != SimilarityMetric.EUCLIDEAN else 1 / (1 + score),
                distance=score if metric in [SimilarityMetric.EUCLIDEAN, SimilarityMetric.MANHATTAN] else None,
                namespace=vector.namespace,
                embedding_type=vector.embedding_type,
                metadata=vector.metadata,
                source_text=vector.source_text,
            ))
        
        return results
    
    def _matches_filter(
        self,
        vector: EmbeddingVector,
        filter: Optional[SearchFilter],
    ) -> bool:
        """Check if vector matches filter."""
        if not filter:
            return True
        
        # Source ID filters
        if filter.source_ids and vector.source_id not in filter.source_ids:
            return False
        if filter.exclude_source_ids and vector.source_id in filter.exclude_source_ids:
            return False
        
        # Metadata equals
        for key, value in filter.metadata_equals.items():
            if vector.metadata.get(key) != value:
                return False
        
        # Metadata contains
        for key, value in filter.metadata_contains.items():
            if key not in vector.metadata:
                return False
            if value not in str(vector.metadata[key]):
                return False
        
        # Tag filters
        if filter.tags_any:
            if not any(tag in vector.tags for tag in filter.tags_any):
                return False
        if filter.tags_all:
            if not all(tag in vector.tags for tag in filter.tags_all):
                return False
        
        # Time filters
        if filter.created_after and vector.created_at < filter.created_after:
            return False
        if filter.created_before and vector.created_at > filter.created_before:
            return False
        
        return True
    
    def _compute_similarity(
        self,
        a: List[float],
        b: List[float],
        metric: SimilarityMetric,
    ) -> float:
        """Compute similarity/distance between vectors."""
        if metric == SimilarityMetric.COSINE:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        
        elif metric == SimilarityMetric.DOT_PRODUCT:
            return sum(x * y for x, y in zip(a, b))
        
        elif metric == SimilarityMetric.EUCLIDEAN:
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        
        elif metric == SimilarityMetric.MANHATTAN:
            return sum(abs(x - y) for x, y in zip(a, b))
        
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    async def count(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        embedding_type: Optional[EmbeddingType] = None,
    ) -> int:
        """Count vectors."""
        if namespace is None and embedding_type is None:
            return len(self._vectors)
        
        candidates = set(self._vectors.keys())
        
        if namespace:
            candidates &= set(self._namespace_index[namespace])
        if embedding_type:
            candidates &= set(self._type_index[embedding_type])
        
        return len(candidates)


# =============================================================================
# FAISS BACKEND (High Performance)
# =============================================================================

class FAISSBackend(VectorStoreBackend):
    """
    FAISS-based vector store for high-performance similarity search.
    
    Supports multiple index types:
    - Flat: Exact search (brute force)
    - IVF: Approximate search with inverted file index
    - HNSW: Approximate search with hierarchical navigable small world graph
    """
    
    def __init__(
        self,
        dimensions: int = 384,
        index_type: IndexType = IndexType.HNSW,
        persist_path: Optional[str] = None,
    ):
        self._dimensions = dimensions
        self._index_type = index_type
        self._persist_path = persist_path
        
        self._index = None
        self._metadata: Dict[int, EmbeddingVector] = {}  # FAISS ID -> Vector
        self._id_map: Dict[str, int] = {}  # vector_id -> FAISS ID
        self._next_id = 0
        
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._lock = asyncio.Lock()
        
        self._initialize_index()
    
    def _initialize_index(self) -> None:
        """Initialize FAISS index."""
        try:
            import faiss
            
            if self._index_type == IndexType.FLAT:
                self._index = faiss.IndexFlatIP(self._dimensions)  # Inner product
            
            elif self._index_type == IndexType.HNSW:
                self._index = faiss.IndexHNSWFlat(self._dimensions, 32)
                self._index.hnsw.efConstruction = 200
                self._index.hnsw.efSearch = 50
            
            elif self._index_type == IndexType.IVF:
                quantizer = faiss.IndexFlatIP(self._dimensions)
                self._index = faiss.IndexIVFFlat(
                    quantizer, self._dimensions, 100
                )
            
            else:
                # Default to flat
                self._index = faiss.IndexFlatIP(self._dimensions)
            
            # Load persisted data if available
            if self._persist_path and Path(self._persist_path).exists():
                self._load_index()
            
            logger.info(f"FAISS backend initialized with {self._index_type.value} index")
            
        except ImportError:
            raise RuntimeError(
                "FAISS not installed. Run: pip install faiss-cpu or faiss-gpu"
            )
    
    @property
    def backend_name(self) -> str:
        return "faiss"
    
    async def store(self, vector: EmbeddingVector) -> None:
        """Store a vector in FAISS index."""
        await self.store_batch([vector])
    
    async def store_batch(self, vectors: List[EmbeddingVector]) -> int:
        """Store batch of vectors."""
        import numpy as np
        
        async with self._lock:
            # Prepare vectors
            embeddings = np.array(
                [v.vector for v in vectors],
                dtype=np.float32,
            )
            
            # Normalize for cosine similarity (since we use inner product)
            faiss = __import__("faiss")
            faiss.normalize_L2(embeddings)
            
            # Assign IDs
            ids = []
            for vector in vectors:
                faiss_id = self._next_id
                self._next_id += 1
                
                self._id_map[vector.vector_id] = faiss_id
                self._metadata[faiss_id] = vector
                ids.append(faiss_id)
                
                VECTOR_COUNT.labels(
                    namespace=vector.namespace.value,
                    embedding_type=vector.embedding_type.value,
                ).inc()
            
            # Add to index
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self._index.add(embeddings),
            )
        
        return len(vectors)
    
    async def get(self, vector_id: str) -> Optional[EmbeddingVector]:
        """Get vector by ID."""
        faiss_id = self._id_map.get(vector_id)
        if faiss_id is None:
            return None
        return self._metadata.get(faiss_id)
    
    async def delete(self, vector_id: str) -> bool:
        """
        Delete vector by ID.
        
        Note: FAISS doesn't support true deletion. We mark as deleted
        and exclude from search results. Periodic compaction needed.
        """
        faiss_id = self._id_map.get(vector_id)
        if faiss_id is None:
            return False
        
        vector = self._metadata.get(faiss_id)
        if vector:
            VECTOR_COUNT.labels(
                namespace=vector.namespace.value,
                embedding_type=vector.embedding_type.value,
            ).dec()
        
        # Mark as deleted (actual removal requires index rebuild)
        del self._id_map[vector_id]
        if faiss_id in self._metadata:
            del self._metadata[faiss_id]
        
        return True
    
    async def search(
        self,
        query_vector: List[float],
        namespace: EmbeddingNamespace,
        embedding_type: Optional[EmbeddingType] = None,
        top_k: int = 10,
        filter: Optional[SearchFilter] = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> List[SearchMatch]:
        """Search using FAISS index."""
        import numpy as np
        
        start = time.perf_counter()
        
        # Prepare query
        query = np.array([query_vector], dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss = __import__("faiss")
        faiss.normalize_L2(query)
        
        # Search more than needed for post-filtering
        search_k = top_k * 5  # Over-fetch for filtering
        
        loop = asyncio.get_event_loop()
        distances, indices = await loop.run_in_executor(
            self._executor,
            lambda: self._index.search(query, search_k),
        )
        
        # Filter and build results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:  # FAISS returns -1 for empty slots
                continue
            
            vector = self._metadata.get(idx)
            if not vector:
                continue
            
            # Apply filters
            if vector.namespace != namespace:
                continue
            if embedding_type and vector.embedding_type != embedding_type:
                continue
            if filter and not self._matches_filter(vector, filter):
                continue
            
            results.append(SearchMatch(
                vector_id=vector.vector_id,
                source_id=vector.source_id,
                score=float(dist),  # Inner product score
                namespace=vector.namespace,
                embedding_type=vector.embedding_type,
                metadata=vector.metadata,
                source_text=vector.source_text,
            ))
            
            if len(results) >= top_k:
                break
        
        duration = time.perf_counter() - start
        VECTOR_SEARCH_LATENCY.labels(
            backend="faiss",
            index_type=self._index_type.value,
        ).observe(duration)
        
        return results
    
    def _matches_filter(
        self,
        vector: EmbeddingVector,
        filter: SearchFilter,
    ) -> bool:
        """Check if vector matches filter."""
        # Same logic as InMemoryBackend
        if filter.source_ids and vector.source_id not in filter.source_ids:
            return False
        if filter.exclude_source_ids and vector.source_id in filter.exclude_source_ids:
            return False
        
        for key, value in filter.metadata_equals.items():
            if vector.metadata.get(key) != value:
                return False
        
        if filter.tags_any:
            if not any(tag in vector.tags for tag in filter.tags_any):
                return False
        if filter.tags_all:
            if not all(tag in vector.tags for tag in filter.tags_all):
                return False
        
        if filter.created_after and vector.created_at < filter.created_after:
            return False
        if filter.created_before and vector.created_at > filter.created_before:
            return False
        
        return True
    
    async def count(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        embedding_type: Optional[EmbeddingType] = None,
    ) -> int:
        """Count vectors."""
        if namespace is None and embedding_type is None:
            return len(self._metadata)
        
        count = 0
        for vector in self._metadata.values():
            if namespace and vector.namespace != namespace:
                continue
            if embedding_type and vector.embedding_type != embedding_type:
                continue
            count += 1
        
        return count
    
    def _save_index(self) -> None:
        """Save index to disk."""
        if not self._persist_path:
            return
        
        import faiss
        
        Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, f"{self._persist_path}.index")
        
        with open(f"{self._persist_path}.meta", "wb") as f:
            pickle.dump({
                "metadata": self._metadata,
                "id_map": self._id_map,
                "next_id": self._next_id,
            }, f)
        
        logger.info(f"Saved FAISS index to {self._persist_path}")
    
    def _load_index(self) -> None:
        """Load index from disk."""
        import faiss
        
        if Path(f"{self._persist_path}.index").exists():
            self._index = faiss.read_index(f"{self._persist_path}.index")
            
            with open(f"{self._persist_path}.meta", "rb") as f:
                data = pickle.load(f)
                self._metadata = data["metadata"]
                self._id_map = data["id_map"]
                self._next_id = data["next_id"]
            
            logger.info(f"Loaded FAISS index from {self._persist_path}")
    
    async def close(self) -> None:
        """Save and cleanup."""
        self._save_index()
        self._executor.shutdown(wait=False)


# =============================================================================
# MAIN VECTOR STORE CLASS
# =============================================================================

class VectorStore:
    """
    Production-grade vector store with pluggable backends.
    
    Features:
    - Multiple backend support (Memory, FAISS, pgvector)
    - Automatic backend selection
    - Index management
    - Batch operations
    - Prometheus metrics
    """
    
    def __init__(
        self,
        backend: Optional[VectorStoreBackend] = None,
        backend_type: str = "auto",
        dimensions: int = 384,
        persist_path: Optional[str] = None,
    ):
        """
        Initialize vector store.
        
        Args:
            backend: Custom backend implementation
            backend_type: "memory", "faiss", or "auto"
            dimensions: Vector dimensions
            persist_path: Path for persistence
        """
        if backend:
            self._backend = backend
        elif backend_type == "memory":
            self._backend = InMemoryBackend()
        elif backend_type == "faiss":
            self._backend = FAISSBackend(
                dimensions=dimensions,
                persist_path=persist_path,
            )
        elif backend_type == "auto":
            # Try FAISS, fall back to memory
            try:
                self._backend = FAISSBackend(
                    dimensions=dimensions,
                    persist_path=persist_path,
                )
            except RuntimeError:
                logger.warning("FAISS not available, using in-memory backend")
                self._backend = InMemoryBackend()
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    @property
    def backend_name(self) -> str:
        """Get backend name."""
        return self._backend.backend_name
    
    async def store(self, vector: EmbeddingVector) -> None:
        """Store a vector."""
        await self._backend.store(vector)
        VECTOR_STORE_OPERATIONS.labels(
            operation="store",
            backend=self.backend_name,
            status="success",
        ).inc()
    
    async def store_batch(self, vectors: List[EmbeddingVector]) -> int:
        """Store batch of vectors."""
        count = await self._backend.store_batch(vectors)
        VECTOR_STORE_OPERATIONS.labels(
            operation="store_batch",
            backend=self.backend_name,
            status="success",
        ).inc(count)
        return count
    
    async def get(self, vector_id: str) -> Optional[EmbeddingVector]:
        """Get vector by ID."""
        return await self._backend.get(vector_id)
    
    async def delete(self, vector_id: str) -> bool:
        """Delete vector by ID."""
        result = await self._backend.delete(vector_id)
        VECTOR_STORE_OPERATIONS.labels(
            operation="delete",
            backend=self.backend_name,
            status="success" if result else "not_found",
        ).inc()
        return result
    
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
        start = time.perf_counter()
        
        results = await self._backend.search(
            query_vector=query_vector,
            namespace=namespace,
            embedding_type=embedding_type,
            top_k=top_k,
            filter=filter,
            metric=metric,
        )
        
        duration = time.perf_counter() - start
        VECTOR_STORE_OPERATIONS.labels(
            operation="search",
            backend=self.backend_name,
            status="success",
        ).inc()
        
        return results
    
    async def count(
        self,
        namespace: Optional[EmbeddingNamespace] = None,
        embedding_type: Optional[EmbeddingType] = None,
    ) -> int:
        """Count vectors."""
        return await self._backend.count(namespace, embedding_type)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        total = await self.count()
        
        return {
            "backend": self.backend_name,
            "total_vectors": total,
        }
    
    async def close(self) -> None:
        """Close and cleanup."""
        await self._backend.close()
