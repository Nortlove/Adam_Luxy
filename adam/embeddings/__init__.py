# =============================================================================
# ADAM Embeddings Infrastructure (#21)
# =============================================================================

"""
EMBEDDINGS INFRASTRUCTURE

Production-grade vector embeddings for semantic operations in ADAM.

Architecture:
- Generator: Multi-provider embedding generation (OpenAI, Local, Custom)
- Store: High-performance vector storage (FAISS, In-Memory)
- Pipeline: Domain-specific embedding pipelines
- Service: Unified API for all embedding operations

Components:
1. EmbeddingGenerator - Multi-backend embedding generation
   - OpenAI text-embedding-3-* models
   - Sentence Transformers (local)
   - Custom psychological models

2. VectorStore - Scalable vector storage
   - FAISS backend for high-performance search
   - In-memory backend for development
   - Automatic index management

3. EmbeddingPipelines - Domain-specific processing
   - UserProfilePipeline - Psychological profiles
   - BrandProfilePipeline - Brand personality
   - AdCreativePipeline - Ad content matching
   - ProductPipeline - Product descriptions

4. EmbeddingService - Unified API
   - embed_text() - Generate embeddings
   - embed_and_store() - Generate + store
   - search_similar() - Semantic search
   - process_user_profile() - User embedding
   - match_user_to_creatives() - User-ad matching

Usage:
    from adam.embeddings import EmbeddingService
    
    service = EmbeddingService()
    
    # Generate embedding
    vector = await service.embed_text("User loves technology")
    
    # Search similar
    results = await service.search_similar(
        query="tech enthusiast",
        namespace=EmbeddingNamespace.USERS,
    )
    
    # Match user to ads
    matches = await service.match_user_to_creatives(
        user_id="user_123",
        user_profile={"big_five": {"openness": 0.8}},
    )
"""

# Models
from adam.embeddings.models import (
    EmbeddingModel,
    EmbeddingModelSpec,
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
    IndexConfig,
    IndexType,
    IndexStats,
    MODEL_SPECS,
    get_model_spec,
)

# Generator
from adam.embeddings.generator import (
    EmbeddingGenerator,
    EmbeddingProvider,
    OpenAIProvider,
    CohereProvider,
    LocalProvider,
    PsychologicalProvider,
)

# Store
from adam.embeddings.store import (
    VectorStore,
    VectorStoreBackend,
    InMemoryBackend,
    FAISSBackend,
)

# Pipelines
from adam.embeddings.pipeline import (
    EmbeddingPipeline,
    PipelineRegistry,
    UserProfilePipeline,
    BrandProfilePipeline,
    AdCreativePipeline,
    ProductPipeline,
    AudioTranscriptPipeline,
)

# Service
from adam.embeddings.service import EmbeddingService

# pgvector Backend
from adam.embeddings.pgvector import PgVectorBackend

# Monitoring
from adam.embeddings.monitoring import (
    EmbeddingMonitor,
    DashboardSnapshot,
    HealthStatus,
    ComponentHealth,
    GeneratorMetrics,
    StoreMetrics,
    SearchMetrics,
    QualityMetrics,
    create_dashboard_routes,
)

# Maintenance
from adam.embeddings.maintenance import (
    MaintenanceScheduler,
    IndexCompactionJob,
    StaleVectorCleanupJob,
    IndexRebuildJob,
    CacheWarmingJob,
    JobResult,
    JobStatus,
)

__all__ = [
    # Models
    "EmbeddingModel",
    "EmbeddingModelSpec",
    "EmbeddingType",
    "EmbeddingNamespace",
    "EmbeddingVector",
    "SimilarityMetric",
    "SearchFilter",
    "SearchMatch",
    "SimilarityResult",
    "BatchEmbedRequest",
    "BatchEmbedResult",
    "PsychologicalEmbedding",
    "BrandPersonalityEmbedding",
    "AdCreativeEmbedding",
    "IndexConfig",
    "IndexType",
    "IndexStats",
    "MODEL_SPECS",
    "get_model_spec",
    # Generator
    "EmbeddingGenerator",
    "EmbeddingProvider",
    "OpenAIProvider",
    "CohereProvider",
    "LocalProvider",
    "PsychologicalProvider",
    # Store
    "VectorStore",
    "VectorStoreBackend",
    "InMemoryBackend",
    "FAISSBackend",
    # Pipelines
    "EmbeddingPipeline",
    "PipelineRegistry",
    "UserProfilePipeline",
    "BrandProfilePipeline",
    "AdCreativePipeline",
    "ProductPipeline",
    "AudioTranscriptPipeline",
    # Service
    "EmbeddingService",
    # pgvector
    "PgVectorBackend",
    # Monitoring
    "EmbeddingMonitor",
    "DashboardSnapshot",
    "HealthStatus",
    "ComponentHealth",
    "GeneratorMetrics",
    "StoreMetrics",
    "SearchMetrics",
    "QualityMetrics",
    "create_dashboard_routes",
    # Maintenance
    "MaintenanceScheduler",
    "IndexCompactionJob",
    "StaleVectorCleanupJob",
    "IndexRebuildJob",
    "CacheWarmingJob",
    "JobResult",
    "JobStatus",
]
