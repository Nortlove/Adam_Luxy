# =============================================================================
# ADAM Embeddings Unit Tests
# Location: tests/unit/test_embeddings.py
# =============================================================================

"""
EMBEDDINGS UNIT TESTS

Comprehensive tests for the embedding infrastructure:
- Generator tests
- Vector store tests
- Pipeline tests
- Service tests
"""

import pytest
import math
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

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
    PsychologicalEmbedding,
    get_model_spec,
)


# =============================================================================
# MODEL TESTS
# =============================================================================

class TestEmbeddingModels:
    """Tests for embedding models and specs."""
    
    def test_model_spec_lookup(self):
        """Test model specification lookup."""
        spec = get_model_spec(EmbeddingModel.ALL_MINILM_L6)
        
        assert spec.model == EmbeddingModel.ALL_MINILM_L6
        assert spec.dimensions == 384
        assert spec.provider == "local"
    
    def test_openai_model_spec(self):
        """Test OpenAI model specifications."""
        spec = get_model_spec(EmbeddingModel.TEXT_EMBEDDING_3_SMALL)
        
        assert spec.dimensions == 1536
        assert spec.provider == "openai"
        assert spec.max_tokens == 8191
    
    def test_embedding_vector_validation(self):
        """Test embedding vector validation."""
        vector = EmbeddingVector(
            vector_id="vec_test",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            dimensions=5,
            source_id="user_001",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        assert vector.vector_id == "vec_test"
        assert len(vector.vector) == 5
    
    def test_embedding_vector_invalid_nan(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValueError, match="NaN"):
            EmbeddingVector(
                vector_id="vec_test",
                namespace=EmbeddingNamespace.USERS,
                embedding_type=EmbeddingType.USER_PROFILE,
                vector=[0.1, float("nan"), 0.3],
                dimensions=3,
                source_id="user_001",
                model=EmbeddingModel.ALL_MINILM_L6,
            )
    
    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        vec_a = EmbeddingVector(
            vector_id="vec_a",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[1.0, 0.0, 0.0],
            dimensions=3,
            source_id="a",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        vec_b = EmbeddingVector(
            vector_id="vec_b",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[1.0, 0.0, 0.0],
            dimensions=3,
            source_id="b",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        # Identical vectors should have similarity 1.0
        assert vec_a.cosine_similarity(vec_b) == pytest.approx(1.0)
    
    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity for orthogonal vectors."""
        vec_a = EmbeddingVector(
            vector_id="vec_a",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[1.0, 0.0, 0.0],
            dimensions=3,
            source_id="a",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        vec_b = EmbeddingVector(
            vector_id="vec_b",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[0.0, 1.0, 0.0],
            dimensions=3,
            source_id="b",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        # Orthogonal vectors should have similarity 0.0
        assert vec_a.cosine_similarity(vec_b) == pytest.approx(0.0)
    
    def test_l2_norm(self):
        """Test L2 norm computation."""
        vec = EmbeddingVector(
            vector_id="vec",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[3.0, 4.0],  # 3-4-5 triangle
            dimensions=2,
            source_id="test",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        assert vec.l2_norm == pytest.approx(5.0)
    
    def test_normalize(self):
        """Test vector normalization."""
        vec = EmbeddingVector(
            vector_id="vec",
            namespace=EmbeddingNamespace.USERS,
            embedding_type=EmbeddingType.USER_PROFILE,
            vector=[3.0, 4.0],
            dimensions=2,
            source_id="test",
            model=EmbeddingModel.ALL_MINILM_L6,
        )
        
        normalized = vec.normalize()
        
        assert normalized.l2_norm == pytest.approx(1.0)
        assert normalized.vector[0] == pytest.approx(0.6)
        assert normalized.vector[1] == pytest.approx(0.8)


# =============================================================================
# GENERATOR TESTS
# =============================================================================

class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator."""
    
    @pytest.mark.asyncio
    async def test_local_provider_fallback(self):
        """Test that generator falls back when no APIs available."""
        from adam.embeddings.generator import EmbeddingGenerator
        
        # Without API keys, should use local or fallback
        generator = EmbeddingGenerator(
            default_model=EmbeddingModel.ALL_MINILM_L6,
            enable_cache=False,
        )
        
        # Should not raise
        embedding = await generator.embed_text("Test text")
        
        assert len(embedding) > 0
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_batch_embedding(self):
        """Test batch embedding generation."""
        from adam.embeddings.generator import EmbeddingGenerator
        
        generator = EmbeddingGenerator(
            default_model=EmbeddingModel.ALL_MINILM_L6,
            enable_cache=False,
        )
        
        texts = ["Hello world", "Test embedding", "Another text"]
        embeddings = await generator.embed_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) > 0 for e in embeddings)
        
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that caching works."""
        from adam.embeddings.generator import EmbeddingGenerator
        
        generator = EmbeddingGenerator(
            default_model=EmbeddingModel.ALL_MINILM_L6,
            enable_cache=True,
        )
        
        # First call
        emb1 = await generator.embed_text("Cache test")
        
        # Second call should hit cache
        emb2 = await generator.embed_text("Cache test")
        
        assert emb1 == emb2
        assert generator.cache_stats["hits"] >= 1
        
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_embed_with_metadata(self):
        """Test embedding with metadata."""
        from adam.embeddings.generator import EmbeddingGenerator
        
        generator = EmbeddingGenerator(
            default_model=EmbeddingModel.ALL_MINILM_L6,
            enable_cache=False,
        )
        
        embedding, metadata = await generator.embed_with_metadata("Test")
        
        assert len(embedding) > 0
        assert "model" in metadata
        assert "dimensions" in metadata
        assert "latency_ms" in metadata
        
        await generator.close()


# =============================================================================
# VECTOR STORE TESTS
# =============================================================================

class TestVectorStore:
    """Tests for VectorStore."""
    
    @pytest.fixture
    def sample_vectors(self):
        """Create sample vectors for testing."""
        return [
            EmbeddingVector(
                vector_id=f"vec_{i}",
                namespace=EmbeddingNamespace.USERS,
                embedding_type=EmbeddingType.USER_PROFILE,
                vector=[float(i) / 10, 0.5, 0.5],
                dimensions=3,
                source_id=f"user_{i}",
                model=EmbeddingModel.ALL_MINILM_L6,
                metadata={"index": i},
            )
            for i in range(10)
        ]
    
    @pytest.mark.asyncio
    async def test_store_and_get(self, sample_vectors):
        """Test storing and retrieving vectors."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        
        # Store
        await store.store(sample_vectors[0])
        
        # Retrieve
        retrieved = await store.get("vec_0")
        
        assert retrieved is not None
        assert retrieved.vector_id == "vec_0"
        assert retrieved.source_id == "user_0"
    
    @pytest.mark.asyncio
    async def test_store_batch(self, sample_vectors):
        """Test batch storage."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        
        count = await store.store_batch(sample_vectors)
        
        assert count == 10
        assert await store.count() == 10
    
    @pytest.mark.asyncio
    async def test_search(self, sample_vectors):
        """Test similarity search."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        await store.store_batch(sample_vectors)
        
        # Search for vector similar to first one
        results = await store.search(
            query_vector=[0.0, 0.5, 0.5],
            namespace=EmbeddingNamespace.USERS,
            top_k=3,
        )
        
        assert len(results) <= 3
        # First result should be vec_0 (most similar)
        assert results[0].vector_id == "vec_0"
    
    @pytest.mark.asyncio
    async def test_search_with_filter(self, sample_vectors):
        """Test search with metadata filter."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        
        # Add tags to some vectors
        for i, vec in enumerate(sample_vectors):
            if i < 5:
                vec.tags = ["group_a"]
            else:
                vec.tags = ["group_b"]
        
        await store.store_batch(sample_vectors)
        
        # Search only group_a
        filter = SearchFilter(tags_any=["group_a"])
        results = await store.search(
            query_vector=[0.5, 0.5, 0.5],
            namespace=EmbeddingNamespace.USERS,
            top_k=10,
            filter=filter,
        )
        
        # Should only return group_a vectors
        assert all(r.vector_id in [f"vec_{i}" for i in range(5)] for r in results)
    
    @pytest.mark.asyncio
    async def test_delete(self, sample_vectors):
        """Test vector deletion."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        await store.store_batch(sample_vectors)
        
        assert await store.count() == 10
        
        result = await store.delete("vec_0")
        
        assert result is True
        assert await store.count() == 9
        assert await store.get("vec_0") is None
    
    @pytest.mark.asyncio
    async def test_count_by_namespace(self, sample_vectors):
        """Test counting by namespace."""
        from adam.embeddings.store import VectorStore
        
        store = VectorStore(backend_type="memory")
        await store.store_batch(sample_vectors)
        
        count = await store.count(namespace=EmbeddingNamespace.USERS)
        
        assert count == 10


# =============================================================================
# PIPELINE TESTS
# =============================================================================

class TestEmbeddingPipelines:
    """Tests for embedding pipelines."""
    
    @pytest.fixture
    def mock_generator(self):
        """Create mock generator."""
        from adam.embeddings.generator import EmbeddingGenerator
        
        generator = MagicMock(spec=EmbeddingGenerator)
        generator.embed_text = AsyncMock(return_value=[0.1] * 512)
        generator.embed_batch = AsyncMock(return_value=[[0.1] * 512, [0.2] * 512])
        generator.embed_with_metadata = AsyncMock(
            return_value=([0.1] * 512, {"latency_ms": 10})
        )
        
        return generator
    
    @pytest.mark.asyncio
    async def test_user_profile_pipeline(self, mock_generator):
        """Test user profile pipeline."""
        from adam.embeddings.pipeline import UserProfilePipeline
        
        pipeline = UserProfilePipeline(mock_generator)
        
        profile_data = {
            "big_five": {
                "openness": 0.8,
                "conscientiousness": 0.6,
                "extraversion": 0.7,
            },
            "regulatory_focus": {
                "promotion": 0.7,
                "prevention": 0.3,
            },
        }
        
        vector = await pipeline.process(
            content=profile_data,
            source_id="user_001",
        )
        
        assert vector.namespace == EmbeddingNamespace.USERS
        assert vector.embedding_type == EmbeddingType.USER_PROFILE
        assert vector.source_id == "user_001"
    
    @pytest.mark.asyncio
    async def test_psychological_embedding(self, mock_generator):
        """Test psychological embedding creation."""
        from adam.embeddings.pipeline import UserProfilePipeline
        
        pipeline = UserProfilePipeline(mock_generator)
        
        profile_data = {
            "big_five": {
                "openness": 0.8,
                "conscientiousness": 0.6,
                "extraversion": 0.7,
                "agreeableness": 0.5,
                "neuroticism": 0.3,
            },
            "regulatory_focus": {
                "promotion": 0.7,
                "prevention": 0.3,
            },
            "construal_level": 0.6,
            "mechanisms": {
                "social_proof": 0.8,
                "scarcity": 0.4,
            },
        }
        
        emb = await pipeline.create_psychological_embedding(
            user_id="user_001",
            profile=profile_data,
        )
        
        assert emb.user_id == "user_001"
        assert len(emb.big_five_component) == 5
        assert len(emb.regulatory_focus_component) == 2
        assert emb.big_five_component[0] == 0.8  # openness
    
    @pytest.mark.asyncio
    async def test_ad_creative_pipeline(self, mock_generator):
        """Test ad creative pipeline."""
        from adam.embeddings.pipeline import AdCreativePipeline
        
        pipeline = AdCreativePipeline(mock_generator)
        
        creative_data = {
            "headline": "Limited Time Offer!",
            "copy": "Join millions who trust our product.",
            "cta": "Buy Now",
        }
        
        vector = await pipeline.process(
            content=creative_data,
            source_id="creative_001",
        )
        
        assert vector.namespace == EmbeddingNamespace.CREATIVES
        assert vector.embedding_type == EmbeddingType.AD_CREATIVE
        
        # Should detect mechanisms
        assert "mechanism_alignment" in vector.metadata
        assert vector.metadata["mechanism_alignment"]["scarcity"] > 0
        assert vector.metadata["mechanism_alignment"]["social_proof"] > 0
    
    @pytest.mark.asyncio
    async def test_brand_profile_pipeline(self, mock_generator):
        """Test brand profile pipeline."""
        from adam.embeddings.pipeline import BrandProfilePipeline
        
        pipeline = BrandProfilePipeline(mock_generator)
        
        brand_data = {
            "name": "TechBrand",
            "tagline": "Innovation for everyone",
            "archetypes": ["creator", "explorer"],
            "tone": ["enthusiastic", "friendly"],
            "values": ["innovation", "quality"],
        }
        
        vector = await pipeline.process(
            content=brand_data,
            source_id="brand_001",
        )
        
        assert vector.namespace == EmbeddingNamespace.BRANDS
        assert vector.embedding_type == EmbeddingType.BRAND_PROFILE


# =============================================================================
# SERVICE TESTS
# =============================================================================

class TestEmbeddingService:
    """Tests for EmbeddingService."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create embedding service with mocked dependencies."""
        from adam.embeddings.service import EmbeddingService
        
        service = EmbeddingService(
            default_model=EmbeddingModel.ALL_MINILM_L6,
            cache=None,
        )
        
        return service
    
    @pytest.mark.asyncio
    async def test_embed_text(self, embedding_service):
        """Test text embedding."""
        embedding = await embedding_service.embed_text("Hello world")
        
        assert len(embedding) > 0
        await embedding_service.close()
    
    @pytest.mark.asyncio
    async def test_embed_and_store(self, embedding_service):
        """Test embed and store."""
        vector = await embedding_service.embed_and_store(
            text="Test user profile",
            source_id="user_001",
            embedding_type=EmbeddingType.USER_PROFILE,
        )
        
        assert vector.vector_id.startswith("vec_")
        assert vector.source_id == "user_001"
        assert len(vector.vector) > 0
        
        await embedding_service.close()
    
    @pytest.mark.asyncio
    async def test_search_similar(self, embedding_service):
        """Test similarity search."""
        # Store some vectors first
        for i in range(5):
            await embedding_service.embed_and_store(
                text=f"User {i} likes technology",
                source_id=f"user_{i}",
                embedding_type=EmbeddingType.USER_PROFILE,
            )
        
        results = await embedding_service.search_similar(
            query="tech enthusiast",
            namespace=EmbeddingNamespace.USERS,
            top_k=3,
        )
        
        assert len(results.matches) <= 3
        assert results.query_text == "tech enthusiast"
        
        await embedding_service.close()
    
    @pytest.mark.asyncio
    async def test_compute_similarity(self, embedding_service):
        """Test similarity computation."""
        score = await embedding_service.compute_similarity(
            "I love technology",
            "Tech enthusiast",
        )
        
        assert 0.0 <= score <= 1.0
        # Similar texts should have high similarity
        assert score > 0.5
        
        await embedding_service.close()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, embedding_service):
        """Test stats retrieval."""
        stats = await embedding_service.get_stats()
        
        assert "generator" in stats
        assert "store" in stats
        assert "pipelines" in stats
        
        await embedding_service.close()
