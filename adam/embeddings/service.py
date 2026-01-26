# =============================================================================
# ADAM Embedding Service
# Location: adam/embeddings/service.py
# =============================================================================

"""
EMBEDDING SERVICE

Unified service for all embedding operations in the ADAM platform.

Provides:
- Multi-model embedding generation
- Vector storage with FAISS/pgvector
- Semantic search and similarity
- Domain-specific pipelines
- Caching and performance optimization
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from prometheus_client import Counter, Histogram

from adam.embeddings.models import (
    EmbeddingModel,
    EmbeddingType,
    EmbeddingNamespace,
    EmbeddingVector,
    SimilarityMetric,
    SearchFilter,
    SearchMatch,
    SimilarityResult,
    BatchEmbedRequest,
    BatchEmbedResult,
    PsychologicalEmbedding,
    BrandPersonalityEmbedding,
    AdCreativeEmbedding,
    get_model_spec,
)
from adam.embeddings.generator import EmbeddingGenerator
from adam.embeddings.store import VectorStore
from adam.embeddings.pipeline import (
    PipelineRegistry,
    UserProfilePipeline,
    BrandProfilePipeline,
    AdCreativePipeline,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.config.settings import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

EMBEDDING_SERVICE_OPERATIONS = Counter(
    "adam_embedding_service_operations_total",
    "Embedding service operations",
    ["operation", "status"],
)

EMBEDDING_SERVICE_LATENCY = Histogram(
    "adam_embedding_service_latency_seconds",
    "Embedding service operation latency",
    ["operation"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)


# =============================================================================
# EMBEDDING SERVICE
# =============================================================================

class EmbeddingService:
    """
    Unified embedding service for the ADAM platform.
    
    Features:
    - Multi-provider embedding generation (OpenAI, Local, Custom)
    - High-performance vector storage (FAISS, Memory)
    - Domain-specific embedding pipelines
    - Semantic search and similarity computation
    - Redis caching layer
    - Prometheus metrics
    
    Usage:
        service = EmbeddingService()
        
        # Generate and store embedding
        vector = await service.embed_and_store(
            text="User loves tech products",
            source_id="user_123",
            embedding_type=EmbeddingType.USER_PROFILE,
        )
        
        # Search for similar
        results = await service.search_similar(
            query="technology enthusiast",
            namespace=EmbeddingNamespace.USERS,
        )
        
        # Compute similarity
        score = await service.compute_similarity(
            "I love gadgets", "Tech enthusiast"
        )
    """
    
    def __init__(
        self,
        default_model: EmbeddingModel = EmbeddingModel.ALL_MINILM_L6,
        cache: Optional[ADAMRedisCache] = None,
        vector_store: Optional[VectorStore] = None,
        persist_path: Optional[str] = None,
    ):
        """
        Initialize embedding service.
        
        Args:
            default_model: Default embedding model
            cache: Redis cache for embeddings
            vector_store: Custom vector store
            persist_path: Path for vector persistence
        """
        self._settings = get_settings()
        
        # Initialize generator
        self.generator = EmbeddingGenerator(
            default_model=default_model,
            enable_cache=True,
            cache_ttl=self._settings.ttl.embedding_ttl,
        )
        
        # Initialize vector store
        if vector_store:
            self.store = vector_store
        else:
            self.store = VectorStore(
                backend_type="auto",
                dimensions=get_model_spec(default_model).dimensions,
                persist_path=persist_path,
            )
        
        # Initialize pipelines
        self.pipelines = PipelineRegistry(self.generator)
        
        # Redis cache
        self.cache = cache
        
        # Default model
        self.default_model = default_model
    
    # =========================================================================
    # CORE OPERATIONS
    # =========================================================================
    
    async def embed_text(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
    ) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Model to use (defaults to service default)
            
        Returns:
            Embedding vector
        """
        start = time.perf_counter()
        
        try:
            embedding = await self.generator.embed_text(text, model)
            
            EMBEDDING_SERVICE_OPERATIONS.labels(
                operation="embed_text",
                status="success",
            ).inc()
            
            return embedding
            
        except Exception as e:
            EMBEDDING_SERVICE_OPERATIONS.labels(
                operation="embed_text",
                status="error",
            ).inc()
            logger.error(f"Embedding failed: {e}")
            raise
            
        finally:
            duration = time.perf_counter() - start
            EMBEDDING_SERVICE_LATENCY.labels(
                operation="embed_text"
            ).observe(duration)
    
    async def embed_batch(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: Texts to embed
            model: Model to use
            
        Returns:
            List of embedding vectors
        """
        start = time.perf_counter()
        
        try:
            embeddings = await self.generator.embed_batch(texts, model)
            
            EMBEDDING_SERVICE_OPERATIONS.labels(
                operation="embed_batch",
                status="success",
            ).inc(len(texts))
            
            return embeddings
            
        except Exception as e:
            EMBEDDING_SERVICE_OPERATIONS.labels(
                operation="embed_batch",
                status="error",
            ).inc()
            raise
            
        finally:
            duration = time.perf_counter() - start
            EMBEDDING_SERVICE_LATENCY.labels(
                operation="embed_batch"
            ).observe(duration)
    
    async def embed_and_store(
        self,
        text: str,
        source_id: str,
        embedding_type: EmbeddingType,
        namespace: Optional[EmbeddingNamespace] = None,
        model: Optional[EmbeddingModel] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> EmbeddingVector:
        """
        Generate embedding and store in vector database.
        
        Args:
            text: Text to embed
            source_id: Source identifier
            embedding_type: Type of embedding
            namespace: Storage namespace
            model: Model to use
            metadata: Additional metadata
            tags: Tags for filtering
            
        Returns:
            Stored embedding vector
        """
        start = time.perf_counter()
        model = model or self.default_model
        
        # Determine namespace from type if not provided
        if namespace is None:
            namespace = self._type_to_namespace(embedding_type)
        
        # Check cache
        cache_key = f"embed:{namespace.value}:{embedding_type.value}:{source_id}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return EmbeddingVector(**cached)
        
        # Generate embedding
        vector, gen_metadata = await self.generator.embed_with_metadata(text, model)
        
        # Create embedding vector
        embedding = EmbeddingVector(
            vector_id=f"vec_{uuid4().hex[:12]}",
            namespace=namespace,
            embedding_type=embedding_type,
            vector=vector,
            dimensions=len(vector),
            source_id=source_id,
            source_text=text[:500] if len(text) > 500 else text,
            model=model,
            metadata={**(metadata or {}), **gen_metadata},
            tags=tags or [],
            generation_latency_ms=gen_metadata.get("latency_ms"),
        )
        
        # Store in vector database
        await self.store.store(embedding)
        
        # Cache
        if self.cache:
            await self.cache.set(
                cache_key,
                embedding.model_dump(),
                ttl=self._settings.ttl.embedding_ttl,
            )
        
        duration = time.perf_counter() - start
        EMBEDDING_SERVICE_LATENCY.labels(
            operation="embed_and_store"
        ).observe(duration)
        
        return embedding
    
    async def embed_and_store_batch(
        self,
        request: BatchEmbedRequest,
    ) -> BatchEmbedResult:
        """
        Generate and store embeddings for batch of texts.
        
        Args:
            request: Batch embed request
            
        Returns:
            Batch result with vectors and statistics
        """
        start = time.perf_counter()
        request_id = uuid4().hex[:12]
        
        vectors: List[EmbeddingVector] = []
        failed_indices: List[int] = []
        errors: List[str] = []
        total_tokens = 0
        
        try:
            # Generate embeddings
            embeddings = await self.generator.embed_batch(
                request.texts, request.model
            )
            
            # Create and store vectors
            for i, (text, embedding) in enumerate(zip(request.texts, embeddings)):
                try:
                    source_id = (
                        request.source_ids[i] 
                        if request.source_ids 
                        else f"batch_{request_id}_{i}"
                    )
                    
                    metadata = request.common_metadata.copy()
                    if request.per_item_metadata and i < len(request.per_item_metadata):
                        metadata.update(request.per_item_metadata[i])
                    
                    vector = EmbeddingVector(
                        vector_id=f"vec_{uuid4().hex[:12]}",
                        namespace=request.namespace,
                        embedding_type=request.embedding_type,
                        vector=embedding,
                        dimensions=len(embedding),
                        source_id=source_id,
                        source_text=text[:500],
                        model=request.model,
                        metadata=metadata,
                    )
                    
                    await self.store.store(vector)
                    vectors.append(vector)
                    
                except Exception as e:
                    failed_indices.append(i)
                    errors.append(str(e))
            
        except Exception as e:
            errors.append(f"Batch embedding failed: {e}")
            failed_indices = list(range(len(request.texts)))
        
        duration = (time.perf_counter() - start) * 1000
        
        return BatchEmbedResult(
            request_id=request_id,
            vectors=vectors,
            failed_indices=failed_indices,
            errors=errors,
            total_requested=len(request.texts),
            total_succeeded=len(vectors),
            total_failed=len(failed_indices),
            total_duration_ms=duration,
            avg_latency_per_item_ms=duration / len(request.texts) if request.texts else 0,
            total_tokens=total_tokens,
        )
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    async def search_similar(
        self,
        query: str,
        namespace: EmbeddingNamespace,
        embedding_type: Optional[EmbeddingType] = None,
        top_k: int = 10,
        filter: Optional[SearchFilter] = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
        model: Optional[EmbeddingModel] = None,
    ) -> SimilarityResult:
        """
        Search for similar items by text query.
        
        Args:
            query: Query text
            namespace: Namespace to search
            embedding_type: Filter by embedding type
            top_k: Number of results
            filter: Additional filters
            metric: Similarity metric
            model: Model for query embedding
            
        Returns:
            Similarity search result
        """
        start = time.perf_counter()
        query_id = uuid4().hex[:12]
        
        # Generate query embedding
        embed_start = time.perf_counter()
        query_vector = await self.generator.embed_text(query, model)
        embed_duration = (time.perf_counter() - embed_start) * 1000
        
        # Search vector store
        matches = await self.store.search(
            query_vector=query_vector,
            namespace=namespace,
            embedding_type=embedding_type,
            top_k=top_k,
            filter=filter,
            metric=metric,
        )
        
        total_duration = (time.perf_counter() - start) * 1000
        
        EMBEDDING_SERVICE_LATENCY.labels(
            operation="search_similar"
        ).observe(total_duration / 1000)
        
        return SimilarityResult(
            query_id=query_id,
            query_text=query,
            metric=metric,
            top_k=top_k,
            matches=matches,
            total_candidates=await self.store.count(namespace, embedding_type),
            search_duration_ms=total_duration,
            embedding_duration_ms=embed_duration,
        )
    
    async def search_by_vector(
        self,
        query_vector: List[float],
        namespace: EmbeddingNamespace,
        embedding_type: Optional[EmbeddingType] = None,
        top_k: int = 10,
        filter: Optional[SearchFilter] = None,
        metric: SimilarityMetric = SimilarityMetric.COSINE,
    ) -> SimilarityResult:
        """
        Search for similar items by vector.
        
        Args:
            query_vector: Query embedding vector
            namespace: Namespace to search
            embedding_type: Filter by embedding type
            top_k: Number of results
            filter: Additional filters
            metric: Similarity metric
            
        Returns:
            Similarity search result
        """
        start = time.perf_counter()
        query_id = uuid4().hex[:12]
        
        matches = await self.store.search(
            query_vector=query_vector,
            namespace=namespace,
            embedding_type=embedding_type,
            top_k=top_k,
            filter=filter,
            metric=metric,
        )
        
        duration = (time.perf_counter() - start) * 1000
        
        return SimilarityResult(
            query_id=query_id,
            metric=metric,
            top_k=top_k,
            matches=matches,
            total_candidates=await self.store.count(namespace, embedding_type),
            search_duration_ms=duration,
        )
    
    async def compute_similarity(
        self,
        text_a: str,
        text_b: str,
        model: Optional[EmbeddingModel] = None,
    ) -> float:
        """
        Compute cosine similarity between two texts.
        
        Args:
            text_a: First text
            text_b: Second text
            model: Model to use
            
        Returns:
            Similarity score (0-1)
        """
        # Batch embed for efficiency
        embeddings = await self.generator.embed_batch([text_a, text_b], model)
        
        # Compute cosine similarity
        vec_a, vec_b = embeddings[0], embeddings[1]
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    # =========================================================================
    # PIPELINE OPERATIONS
    # =========================================================================
    
    async def process_user_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any],
        store: bool = True,
    ) -> PsychologicalEmbedding:
        """
        Create psychological embedding for user profile.
        
        Args:
            user_id: User identifier
            profile_data: Profile data with traits
            store: Whether to store in vector database
            
        Returns:
            Psychological embedding
        """
        pipeline: UserProfilePipeline = self.pipelines.get("user_profile")
        embedding = await pipeline.create_psychological_embedding(
            user_id, profile_data
        )
        
        if store:
            vector = EmbeddingVector(
                vector_id=f"psych_{uuid4().hex[:12]}",
                namespace=EmbeddingNamespace.USERS,
                embedding_type=EmbeddingType.PSYCHOLOGICAL_CONSTRUCT,
                vector=embedding.vector,
                dimensions=embedding.dimensions,
                source_id=user_id,
                model=EmbeddingModel.PSYCHOLOGICAL_BASE,
                metadata={
                    "confidence": embedding.confidence,
                    "data_points": embedding.data_points,
                },
            )
            await self.store.store(vector)
        
        return embedding
    
    async def process_brand_profile(
        self,
        brand_id: str,
        brand_data: Dict[str, Any],
        store: bool = True,
    ) -> BrandPersonalityEmbedding:
        """
        Create brand personality embedding.
        
        Args:
            brand_id: Brand identifier
            brand_data: Brand data with archetypes
            store: Whether to store
            
        Returns:
            Brand personality embedding
        """
        pipeline: BrandProfilePipeline = self.pipelines.get("brand_profile")
        embedding = await pipeline.create_brand_embedding(brand_id, brand_data)
        
        if store:
            vector = EmbeddingVector(
                vector_id=f"brand_{uuid4().hex[:12]}",
                namespace=EmbeddingNamespace.BRANDS,
                embedding_type=EmbeddingType.BRAND_PROFILE,
                vector=embedding.vector,
                dimensions=embedding.dimensions,
                source_id=brand_id,
                model=EmbeddingModel.BRAND_PERSONALITY,
                metadata={
                    "archetypes": brand_data.get("archetypes", []),
                },
            )
            await self.store.store(vector)
        
        return embedding
    
    async def process_ad_creative(
        self,
        creative_id: str,
        campaign_id: str,
        brand_id: str,
        creative_data: Dict[str, Any],
        store: bool = True,
    ) -> AdCreativeEmbedding:
        """
        Create ad creative embedding.
        
        Args:
            creative_id: Creative identifier
            campaign_id: Campaign identifier
            brand_id: Brand identifier
            creative_data: Creative content
            store: Whether to store
            
        Returns:
            Ad creative embedding
        """
        pipeline: AdCreativePipeline = self.pipelines.get("ad_creative")
        embedding = await pipeline.create_ad_embedding(
            creative_id, campaign_id, brand_id, creative_data
        )
        
        if store:
            vector = EmbeddingVector(
                vector_id=f"creative_{uuid4().hex[:12]}",
                namespace=EmbeddingNamespace.CREATIVES,
                embedding_type=EmbeddingType.AD_CREATIVE,
                vector=embedding.vector,
                dimensions=embedding.dimensions,
                source_id=creative_id,
                model=EmbeddingModel.ADVERTISING_CREATIVE,
                metadata={
                    "campaign_id": campaign_id,
                    "brand_id": brand_id,
                    "mechanism_alignment": embedding.mechanism_alignment,
                },
            )
            await self.store.store(vector)
        
        return embedding
    
    # =========================================================================
    # MATCHING OPERATIONS
    # =========================================================================
    
    async def match_user_to_brands(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Match user to brands based on psychological alignment.
        
        Args:
            user_id: User identifier
            user_profile: User profile data
            top_k: Number of matches
            
        Returns:
            List of (brand_id, similarity_score) tuples
        """
        # Get user embedding
        user_emb = await self.process_user_profile(user_id, user_profile, store=False)
        
        # Search brands
        results = await self.search_by_vector(
            query_vector=user_emb.vector,
            namespace=EmbeddingNamespace.BRANDS,
            embedding_type=EmbeddingType.BRAND_PROFILE,
            top_k=top_k,
        )
        
        return [(m.source_id, m.score) for m in results.matches]
    
    async def match_user_to_creatives(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        campaign_ids: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Match user to ad creatives.
        
        Args:
            user_id: User identifier
            user_profile: User profile data
            campaign_ids: Optional campaign filter
            top_k: Number of matches
            
        Returns:
            List of (creative_id, score, mechanism_alignment) tuples
        """
        # Get user embedding
        user_emb = await self.process_user_profile(user_id, user_profile, store=False)
        
        # Build filter
        search_filter = None
        if campaign_ids:
            search_filter = SearchFilter(
                metadata_equals={"campaign_id": campaign_ids[0]}
                if len(campaign_ids) == 1 else {}
            )
        
        # Search creatives
        results = await self.search_by_vector(
            query_vector=user_emb.vector,
            namespace=EmbeddingNamespace.CREATIVES,
            embedding_type=EmbeddingType.AD_CREATIVE,
            top_k=top_k,
            filter=search_filter,
        )
        
        return [
            (
                m.source_id,
                m.score,
                m.metadata.get("mechanism_alignment", {}),
            )
            for m in results.matches
        ]
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _type_to_namespace(self, embedding_type: EmbeddingType) -> EmbeddingNamespace:
        """Map embedding type to default namespace."""
        mapping = {
            EmbeddingType.USER_PROFILE: EmbeddingNamespace.USERS,
            EmbeddingType.USER_BEHAVIOR_SEQUENCE: EmbeddingNamespace.USERS,
            EmbeddingType.USER_PREFERENCE: EmbeddingNamespace.USERS,
            EmbeddingType.BRAND_PROFILE: EmbeddingNamespace.BRANDS,
            EmbeddingType.BRAND_VOICE: EmbeddingNamespace.BRANDS,
            EmbeddingType.BRAND_VALUES: EmbeddingNamespace.BRANDS,
            EmbeddingType.AD_CREATIVE: EmbeddingNamespace.CREATIVES,
            EmbeddingType.AD_COPY: EmbeddingNamespace.CREATIVES,
            EmbeddingType.AD_HEADLINE: EmbeddingNamespace.CREATIVES,
            EmbeddingType.AD_CTA: EmbeddingNamespace.CREATIVES,
            EmbeddingType.PRODUCT_DESCRIPTION: EmbeddingNamespace.PRODUCTS,
            EmbeddingType.PRODUCT_CATEGORY: EmbeddingNamespace.PRODUCTS,
            EmbeddingType.PRODUCT_REVIEW: EmbeddingNamespace.PRODUCTS,
            EmbeddingType.PSYCHOLOGICAL_CONSTRUCT: EmbeddingNamespace.PSYCHOLOGY,
            EmbeddingType.MECHANISM_DESCRIPTION: EmbeddingNamespace.PSYCHOLOGY,
            EmbeddingType.PERSONALITY_PROFILE: EmbeddingNamespace.PSYCHOLOGY,
            EmbeddingType.AUDIO_TRANSCRIPT: EmbeddingNamespace.AUDIO,
            EmbeddingType.AUDIO_FEATURES: EmbeddingNamespace.AUDIO,
            EmbeddingType.SEMANTIC_QUERY: EmbeddingNamespace.QUERIES,
            EmbeddingType.DOCUMENT: EmbeddingNamespace.QUERIES,
        }
        return mapping.get(embedding_type, EmbeddingNamespace.QUERIES)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        store_stats = await self.store.get_stats()
        cache_stats = self.generator.cache_stats
        
        return {
            "generator": {
                "default_model": self.default_model.value,
                "cache": cache_stats,
            },
            "store": store_stats,
            "pipelines": self.pipelines.list_pipelines(),
        }
    
    async def close(self) -> None:
        """Close all resources."""
        await self.generator.close()
        await self.store.close()
