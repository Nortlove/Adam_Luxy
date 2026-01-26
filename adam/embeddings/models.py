# =============================================================================
# ADAM Embeddings Models
# Location: adam/embeddings/models.py
# =============================================================================

"""
EMBEDDINGS MODELS

Comprehensive models for vector embeddings, similarity search, and semantic
operations in the ADAM platform.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import math

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# EMBEDDING MODEL TYPES
# =============================================================================

class EmbeddingModel(str, Enum):
    """Available embedding models with their specifications."""
    
    # OpenAI Models (Cloud)
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"
    
    # Sentence Transformers (Local)
    ALL_MINILM_L6 = "all-MiniLM-L6-v2"
    ALL_MPNET_BASE = "all-mpnet-base-v2"
    MULTI_QA_MPNET_BASE = "multi-qa-mpnet-base-dot-v1"
    PARAPHRASE_MULTILINGUAL = "paraphrase-multilingual-MiniLM-L12-v2"
    
    # Domain-Specific Models
    PSYCHOLOGICAL_BASE = "adam-psychological-v1"
    ADVERTISING_CREATIVE = "adam-ad-creative-v1"
    BRAND_PERSONALITY = "adam-brand-personality-v1"
    USER_BEHAVIOR = "adam-user-behavior-v1"
    
    # Cohere Models
    COHERE_EMBED_ENGLISH = "embed-english-v3.0"
    COHERE_EMBED_MULTILINGUAL = "embed-multilingual-v3.0"


class EmbeddingModelSpec(BaseModel):
    """Specification for an embedding model."""
    
    model: EmbeddingModel
    dimensions: int
    max_tokens: int
    provider: str  # openai, local, cohere, custom
    supports_batch: bool = True
    supports_truncation: bool = True
    normalized: bool = True  # Whether outputs are L2 normalized
    
    # Performance characteristics
    avg_latency_ms: float = 50.0
    cost_per_1k_tokens: float = 0.0


# Model specifications registry
MODEL_SPECS: Dict[EmbeddingModel, EmbeddingModelSpec] = {
    EmbeddingModel.TEXT_EMBEDDING_3_SMALL: EmbeddingModelSpec(
        model=EmbeddingModel.TEXT_EMBEDDING_3_SMALL,
        dimensions=1536,
        max_tokens=8191,
        provider="openai",
        avg_latency_ms=100,
        cost_per_1k_tokens=0.00002,
    ),
    EmbeddingModel.TEXT_EMBEDDING_3_LARGE: EmbeddingModelSpec(
        model=EmbeddingModel.TEXT_EMBEDDING_3_LARGE,
        dimensions=3072,
        max_tokens=8191,
        provider="openai",
        avg_latency_ms=150,
        cost_per_1k_tokens=0.00013,
    ),
    EmbeddingModel.TEXT_EMBEDDING_ADA_002: EmbeddingModelSpec(
        model=EmbeddingModel.TEXT_EMBEDDING_ADA_002,
        dimensions=1536,
        max_tokens=8191,
        provider="openai",
        avg_latency_ms=80,
        cost_per_1k_tokens=0.0001,
    ),
    EmbeddingModel.ALL_MINILM_L6: EmbeddingModelSpec(
        model=EmbeddingModel.ALL_MINILM_L6,
        dimensions=384,
        max_tokens=512,
        provider="local",
        avg_latency_ms=10,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.ALL_MPNET_BASE: EmbeddingModelSpec(
        model=EmbeddingModel.ALL_MPNET_BASE,
        dimensions=768,
        max_tokens=512,
        provider="local",
        avg_latency_ms=20,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.MULTI_QA_MPNET_BASE: EmbeddingModelSpec(
        model=EmbeddingModel.MULTI_QA_MPNET_BASE,
        dimensions=768,
        max_tokens=512,
        provider="local",
        avg_latency_ms=20,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.PSYCHOLOGICAL_BASE: EmbeddingModelSpec(
        model=EmbeddingModel.PSYCHOLOGICAL_BASE,
        dimensions=512,
        max_tokens=512,
        provider="custom",
        avg_latency_ms=15,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.ADVERTISING_CREATIVE: EmbeddingModelSpec(
        model=EmbeddingModel.ADVERTISING_CREATIVE,
        dimensions=768,
        max_tokens=1024,
        provider="custom",
        avg_latency_ms=25,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.BRAND_PERSONALITY: EmbeddingModelSpec(
        model=EmbeddingModel.BRAND_PERSONALITY,
        dimensions=512,
        max_tokens=512,
        provider="custom",
        avg_latency_ms=15,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.USER_BEHAVIOR: EmbeddingModelSpec(
        model=EmbeddingModel.USER_BEHAVIOR,
        dimensions=256,
        max_tokens=256,
        provider="custom",
        avg_latency_ms=8,
        cost_per_1k_tokens=0.0,
    ),
    EmbeddingModel.COHERE_EMBED_ENGLISH: EmbeddingModelSpec(
        model=EmbeddingModel.COHERE_EMBED_ENGLISH,
        dimensions=1024,
        max_tokens=512,
        provider="cohere",
        avg_latency_ms=80,
        cost_per_1k_tokens=0.0001,
    ),
    EmbeddingModel.COHERE_EMBED_MULTILINGUAL: EmbeddingModelSpec(
        model=EmbeddingModel.COHERE_EMBED_MULTILINGUAL,
        dimensions=1024,
        max_tokens=512,
        provider="cohere",
        avg_latency_ms=100,
        cost_per_1k_tokens=0.0001,
    ),
}


def get_model_spec(model: EmbeddingModel) -> EmbeddingModelSpec:
    """Get specification for a model."""
    return MODEL_SPECS.get(model, MODEL_SPECS[EmbeddingModel.ALL_MINILM_L6])


# =============================================================================
# EMBEDDING TYPES
# =============================================================================

class EmbeddingType(str, Enum):
    """Types of content being embedded."""
    
    # User-related
    USER_PROFILE = "user_profile"
    USER_BEHAVIOR_SEQUENCE = "user_behavior_sequence"
    USER_PREFERENCE = "user_preference"
    
    # Brand-related
    BRAND_PROFILE = "brand_profile"
    BRAND_VOICE = "brand_voice"
    BRAND_VALUES = "brand_values"
    
    # Ad Creative
    AD_CREATIVE = "ad_creative"
    AD_COPY = "ad_copy"
    AD_HEADLINE = "ad_headline"
    AD_CTA = "ad_cta"
    
    # Product
    PRODUCT_DESCRIPTION = "product_description"
    PRODUCT_CATEGORY = "product_category"
    PRODUCT_REVIEW = "product_review"
    
    # Psychological
    PSYCHOLOGICAL_CONSTRUCT = "psychological_construct"
    MECHANISM_DESCRIPTION = "mechanism_description"
    PERSONALITY_PROFILE = "personality_profile"
    
    # Audio
    AUDIO_TRANSCRIPT = "audio_transcript"
    AUDIO_FEATURES = "audio_features"
    
    # General
    SEMANTIC_QUERY = "semantic_query"
    DOCUMENT = "document"


class EmbeddingNamespace(str, Enum):
    """Logical namespaces for embedding storage."""
    
    USERS = "users"
    BRANDS = "brands"
    CREATIVES = "creatives"
    PRODUCTS = "products"
    PSYCHOLOGY = "psychology"
    AUDIO = "audio"
    QUERIES = "queries"


# =============================================================================
# EMBEDDING VECTOR
# =============================================================================

class EmbeddingVector(BaseModel):
    """An embedding vector with full metadata."""
    
    # Identity
    vector_id: str
    namespace: EmbeddingNamespace
    embedding_type: EmbeddingType
    
    # Vector data
    vector: List[float]
    dimensions: int = Field(ge=1)
    
    # Source information
    source_id: str
    source_text: Optional[str] = None  # Original text (truncated)
    source_hash: Optional[str] = None  # Hash for deduplication
    
    # Model information
    model: EmbeddingModel
    model_version: str = "1.0"
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    # Timing and versioning
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = None
    version: int = 1
    
    # Quality metrics
    generation_latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    
    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Ensure vector is valid."""
        if not v:
            raise ValueError("Vector cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Vector must contain only numbers")
        if any(math.isnan(x) or math.isinf(x) for x in v):
            raise ValueError("Vector contains NaN or Inf values")
        return v
    
    def cosine_similarity(self, other: "EmbeddingVector") -> float:
        """Compute cosine similarity with another vector."""
        if len(self.vector) != len(other.vector):
            raise ValueError(
                f"Dimension mismatch: {len(self.vector)} vs {len(other.vector)}"
            )
        
        dot = sum(a * b for a, b in zip(self.vector, other.vector))
        norm_a = math.sqrt(sum(a * a for a in self.vector))
        norm_b = math.sqrt(sum(b * b for b in other.vector))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def euclidean_distance(self, other: "EmbeddingVector") -> float:
        """Compute Euclidean distance to another vector."""
        if len(self.vector) != len(other.vector):
            raise ValueError("Dimension mismatch")
        
        return math.sqrt(
            sum((a - b) ** 2 for a, b in zip(self.vector, other.vector))
        )
    
    def dot_product(self, other: "EmbeddingVector") -> float:
        """Compute dot product with another vector."""
        if len(self.vector) != len(other.vector):
            raise ValueError("Dimension mismatch")
        
        return sum(a * b for a, b in zip(self.vector, other.vector))
    
    @property
    def l2_norm(self) -> float:
        """Compute L2 norm of the vector."""
        return math.sqrt(sum(x * x for x in self.vector))
    
    def normalize(self) -> "EmbeddingVector":
        """Return L2-normalized version of this vector."""
        norm = self.l2_norm
        if norm == 0:
            return self
        
        normalized = [x / norm for x in self.vector]
        return self.model_copy(update={"vector": normalized})


# =============================================================================
# SEARCH MODELS
# =============================================================================

class SimilarityMetric(str, Enum):
    """Distance/similarity metrics for search."""
    
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"
    MANHATTAN = "manhattan"


class SearchFilter(BaseModel):
    """Filter conditions for vector search."""
    
    # Metadata filters
    metadata_equals: Dict[str, Any] = Field(default_factory=dict)
    metadata_contains: Dict[str, Any] = Field(default_factory=dict)
    
    # Tag filters
    tags_any: List[str] = Field(default_factory=list)
    tags_all: List[str] = Field(default_factory=list)
    
    # Type filters
    embedding_types: List[EmbeddingType] = Field(default_factory=list)
    namespaces: List[EmbeddingNamespace] = Field(default_factory=list)
    
    # Time filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Source filters
    source_ids: List[str] = Field(default_factory=list)
    exclude_source_ids: List[str] = Field(default_factory=list)


class SearchMatch(BaseModel):
    """A single search result match."""
    
    vector_id: str
    source_id: str
    score: float  # Similarity score (higher = more similar)
    distance: Optional[float] = None  # Raw distance (lower = more similar)
    
    # Vector data (optional, for efficiency)
    vector: Optional[List[float]] = None
    
    # Metadata
    namespace: EmbeddingNamespace
    embedding_type: EmbeddingType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_text: Optional[str] = None


class SimilarityResult(BaseModel):
    """Result of a similarity search."""
    
    query_id: str
    
    # Search configuration
    query_text: Optional[str] = None
    query_vector_id: Optional[str] = None
    metric: SimilarityMetric = SimilarityMetric.COSINE
    top_k: int = Field(ge=1)
    
    # Results
    matches: List[SearchMatch] = Field(default_factory=list)
    total_candidates: int = 0
    
    # Performance
    search_duration_ms: float = Field(ge=0.0)
    embedding_duration_ms: Optional[float] = None
    
    # Timestamp
    searched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    @property
    def best_match(self) -> Optional[SearchMatch]:
        """Get the best matching result."""
        return self.matches[0] if self.matches else None
    
    @property
    def match_count(self) -> int:
        """Number of matches returned."""
        return len(self.matches)


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

class BatchEmbedRequest(BaseModel):
    """Request for batch embedding generation."""
    
    texts: List[str]
    model: EmbeddingModel = EmbeddingModel.ALL_MINILM_L6
    namespace: EmbeddingNamespace
    embedding_type: EmbeddingType
    
    # Optional source IDs (must match length of texts)
    source_ids: Optional[List[str]] = None
    
    # Common metadata for all embeddings
    common_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Per-item metadata (must match length of texts)
    per_item_metadata: Optional[List[Dict[str, Any]]] = None
    
    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        """Ensure texts are valid."""
        if not v:
            raise ValueError("At least one text required")
        if len(v) > 1000:
            raise ValueError("Maximum batch size is 1000")
        return v


class BatchEmbedResult(BaseModel):
    """Result of batch embedding generation."""
    
    request_id: str
    
    # Results
    vectors: List[EmbeddingVector] = Field(default_factory=list)
    failed_indices: List[int] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Statistics
    total_requested: int
    total_succeeded: int
    total_failed: int
    
    # Performance
    total_duration_ms: float
    avg_latency_per_item_ms: float
    total_tokens: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requested == 0:
            return 0.0
        return self.total_succeeded / self.total_requested


# =============================================================================
# PSYCHOLOGICAL EMBEDDING MODELS
# =============================================================================

class PsychologicalEmbedding(BaseModel):
    """
    Specialized embedding for psychological constructs.
    
    Captures Big Five traits, regulatory focus, construal level,
    and mechanism affinities in a unified semantic space.
    """
    
    user_id: str
    
    # Core embedding
    vector: List[float]
    dimensions: int = 512
    
    # Psychological components (interpretable)
    big_five_component: List[float] = Field(default_factory=list)  # 5-dim
    regulatory_focus_component: List[float] = Field(default_factory=list)  # 2-dim
    construal_level_component: List[float] = Field(default_factory=list)  # 1-dim
    mechanism_affinity_component: List[float] = Field(default_factory=list)  # N-dim
    
    # Confidence and quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    data_points: int = 0
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    model_version: str = "1.0"


class BrandPersonalityEmbedding(BaseModel):
    """
    Embedding for brand personality and voice.
    
    Captures brand archetypes, tone, values in semantic space
    for matching with user psychological profiles.
    """
    
    brand_id: str
    
    # Core embedding
    vector: List[float]
    dimensions: int = 512
    
    # Brand components (interpretable)
    archetype_component: List[float] = Field(default_factory=list)  # 12-dim
    tone_component: List[float] = Field(default_factory=list)  # 8-dim
    values_component: List[float] = Field(default_factory=list)  # 10-dim
    
    # Target audience profile
    target_big_five: Optional[List[float]] = None
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AdCreativeEmbedding(BaseModel):
    """
    Embedding for ad creative content.
    
    Captures semantic meaning, emotional tone, persuasion style,
    and mechanism alignment for ad-user matching.
    """
    
    creative_id: str
    campaign_id: str
    brand_id: str
    
    # Core embedding
    vector: List[float]
    dimensions: int = 768
    
    # Creative components
    semantic_component: List[float] = Field(default_factory=list)
    emotional_component: List[float] = Field(default_factory=list)
    persuasion_component: List[float] = Field(default_factory=list)
    
    # Mechanism alignment scores
    mechanism_alignment: Dict[str, float] = Field(default_factory=dict)
    
    # Content metadata
    copy_text: Optional[str] = None
    headline: Optional[str] = None
    cta: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# INDEX MODELS
# =============================================================================

class IndexType(str, Enum):
    """Types of vector indices."""
    
    FLAT = "flat"  # Exact search (brute force)
    IVF = "ivf"  # Inverted file index
    HNSW = "hnsw"  # Hierarchical navigable small world
    PQ = "pq"  # Product quantization
    IVF_PQ = "ivf_pq"  # Combined


class IndexConfig(BaseModel):
    """Configuration for a vector index."""
    
    name: str
    namespace: EmbeddingNamespace
    embedding_type: EmbeddingType
    dimensions: int
    
    # Index type
    index_type: IndexType = IndexType.HNSW
    metric: SimilarityMetric = SimilarityMetric.COSINE
    
    # HNSW parameters
    hnsw_m: int = 16  # Max connections per layer
    hnsw_ef_construction: int = 200  # Construction-time search breadth
    hnsw_ef_search: int = 50  # Search-time breadth
    
    # IVF parameters
    ivf_nlist: int = 100  # Number of clusters
    ivf_nprobe: int = 10  # Clusters to search
    
    # PQ parameters
    pq_m: int = 8  # Number of sub-quantizers
    pq_nbits: int = 8  # Bits per sub-quantizer
    
    # Status
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    vector_count: int = 0
    is_trained: bool = False


class IndexStats(BaseModel):
    """Statistics for a vector index."""
    
    name: str
    vector_count: int
    dimensions: int
    
    # Memory usage
    memory_usage_bytes: int = 0
    
    # Performance
    avg_search_latency_ms: float = 0.0
    queries_per_second: float = 0.0
    
    # Quality
    recall_at_10: Optional[float] = None
    recall_at_100: Optional[float] = None
