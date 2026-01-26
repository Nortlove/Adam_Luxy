# =============================================================================
# ADAM Embedding Generator
# Location: adam/embeddings/generator.py
# =============================================================================

"""
EMBEDDING GENERATOR

Production-grade embedding generation with multi-provider support,
batch processing, caching, and domain-specific models.
"""

import asyncio
import hashlib
import logging
import os
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Type

import httpx
from prometheus_client import Counter, Histogram

from adam.embeddings.models import (
    EmbeddingModel,
    EmbeddingModelSpec,
    MODEL_SPECS,
    get_model_spec,
)
from adam.config.settings import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

EMBEDDING_REQUESTS = Counter(
    "adam_embedding_requests_total",
    "Total embedding generation requests",
    ["provider", "model", "status"],
)

EMBEDDING_LATENCY = Histogram(
    "adam_embedding_latency_seconds",
    "Embedding generation latency",
    ["provider", "model"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

EMBEDDING_TOKENS = Counter(
    "adam_embedding_tokens_total",
    "Total tokens processed for embeddings",
    ["provider", "model"],
)

BATCH_SIZE = Histogram(
    "adam_embedding_batch_size",
    "Embedding batch sizes",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
)


# =============================================================================
# BASE PROVIDER
# =============================================================================

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[EmbeddingModel]:
        """List of supported models."""
        pass
    
    @abstractmethod
    async def embed_single(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        Embed a single text.
        
        Returns:
            Tuple of (embedding vector, metadata dict with tokens etc.)
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """
        Embed a batch of texts.
        
        Returns:
            Tuple of (list of embeddings, metadata dict)
        """
        pass
    
    async def close(self) -> None:
        """Clean up resources."""
        pass


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://api.openai.com/v1"
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def supported_models(self) -> List[EmbeddingModel]:
        return [
            EmbeddingModel.TEXT_EMBEDDING_3_SMALL,
            EmbeddingModel.TEXT_EMBEDDING_3_LARGE,
            EmbeddingModel.TEXT_EMBEDDING_ADA_002,
        ]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client
    
    async def embed_single(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """Embed single text via OpenAI API."""
        embeddings, metadata = await self.embed_batch([text], model)
        return embeddings[0], metadata
    
    async def embed_batch(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """Embed batch via OpenAI API."""
        if not self._api_key:
            raise ValueError("OpenAI API key not configured")
        
        client = await self._get_client()
        
        # OpenAI supports up to 2048 inputs per request
        # For larger batches, we need to chunk
        max_batch = 2048
        all_embeddings = []
        total_tokens = 0
        
        for i in range(0, len(texts), max_batch):
            batch = texts[i:i + max_batch]
            
            response = await client.post(
                "/embeddings",
                json={
                    "input": batch,
                    "model": model.value,
                    "encoding_format": "float",
                },
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"OpenAI API error: {response.status_code} - {error_detail}")
                raise RuntimeError(f"OpenAI API error: {response.status_code}")
            
            data = response.json()
            
            # Extract embeddings in correct order
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            batch_embeddings = [item["embedding"] for item in sorted_data]
            all_embeddings.extend(batch_embeddings)
            
            total_tokens += data.get("usage", {}).get("total_tokens", 0)
        
        return all_embeddings, {"tokens": total_tokens, "model": model.value}
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# =============================================================================
# COHERE PROVIDER
# =============================================================================

class CohereProvider(EmbeddingProvider):
    """Cohere embedding provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("COHERE_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None
        self._base_url = "https://api.cohere.ai/v1"
    
    @property
    def provider_name(self) -> str:
        return "cohere"
    
    @property
    def supported_models(self) -> List[EmbeddingModel]:
        return [
            EmbeddingModel.COHERE_EMBED_ENGLISH,
            EmbeddingModel.COHERE_EMBED_MULTILINGUAL,
        ]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client
    
    async def embed_single(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """Embed single text via Cohere API."""
        embeddings, metadata = await self.embed_batch([text], model)
        return embeddings[0], metadata
    
    async def embed_batch(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """Embed batch via Cohere API."""
        if not self._api_key:
            raise ValueError("Cohere API key not configured")
        
        client = await self._get_client()
        
        # Cohere supports up to 96 texts per request
        max_batch = 96
        all_embeddings = []
        
        for i in range(0, len(texts), max_batch):
            batch = texts[i:i + max_batch]
            
            response = await client.post(
                "/embed",
                json={
                    "texts": batch,
                    "model": model.value,
                    "input_type": "search_document",
                    "truncate": "END",
                },
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Cohere API error: {response.status_code}")
            
            data = response.json()
            all_embeddings.extend(data["embeddings"])
        
        return all_embeddings, {"model": model.value}
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# =============================================================================
# LOCAL PROVIDER (SENTENCE TRANSFORMERS)
# =============================================================================

class LocalProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""
    
    def __init__(self, device: str = "cpu"):
        self._device = device
        self._models: Dict[str, Any] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._lock = asyncio.Lock()
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    @property
    def supported_models(self) -> List[EmbeddingModel]:
        return [
            EmbeddingModel.ALL_MINILM_L6,
            EmbeddingModel.ALL_MPNET_BASE,
            EmbeddingModel.MULTI_QA_MPNET_BASE,
            EmbeddingModel.PARAPHRASE_MULTILINGUAL,
        ]
    
    def _get_model(self, model: EmbeddingModel):
        """Get or load a sentence-transformers model."""
        if model.value not in self._models:
            try:
                from sentence_transformers import SentenceTransformer
                
                self._models[model.value] = SentenceTransformer(
                    model.value,
                    device=self._device,
                )
                logger.info(f"Loaded sentence-transformers model: {model.value}")
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
        
        return self._models[model.value]
    
    async def embed_single(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """Embed single text locally."""
        embeddings, metadata = await self.embed_batch([text], model)
        return embeddings[0], metadata
    
    async def embed_batch(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """Embed batch locally using thread pool."""
        async with self._lock:
            st_model = self._get_model(model)
        
        loop = asyncio.get_event_loop()
        
        def _encode():
            embeddings = st_model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        
        embeddings = await loop.run_in_executor(self._executor, _encode)
        
        return embeddings, {"model": model.value}
    
    async def close(self) -> None:
        """Shutdown executor."""
        self._executor.shutdown(wait=False)


# =============================================================================
# PSYCHOLOGICAL EMBEDDING PROVIDER
# =============================================================================

class PsychologicalProvider(EmbeddingProvider):
    """
    Custom provider for psychological embeddings.
    
    Uses a combination of:
    1. Base semantic embeddings (sentence-transformers)
    2. Psychological feature projections
    3. Domain-specific fine-tuning layers
    """
    
    def __init__(self, base_provider: Optional[LocalProvider] = None):
        self._base_provider = base_provider or LocalProvider()
        self._psychological_weights: Optional[Any] = None
        self._brand_weights: Optional[Any] = None
        
        # Psychological construct keywords for feature extraction
        self._construct_keywords = {
            "openness": [
                "creative", "artistic", "curious", "imaginative", "original",
                "inventive", "unconventional", "intellectual", "complex",
            ],
            "conscientiousness": [
                "organized", "reliable", "disciplined", "careful", "thorough",
                "responsible", "hardworking", "efficient", "systematic",
            ],
            "extraversion": [
                "outgoing", "social", "energetic", "talkative", "assertive",
                "active", "enthusiastic", "bold", "adventurous",
            ],
            "agreeableness": [
                "kind", "cooperative", "trusting", "helpful", "empathetic",
                "generous", "friendly", "compassionate", "warm",
            ],
            "neuroticism": [
                "anxious", "worried", "nervous", "sensitive", "emotional",
                "stressed", "moody", "insecure", "tense",
            ],
            "promotion_focus": [
                "achieve", "gain", "aspire", "advance", "grow", "succeed",
                "opportunity", "potential", "goal", "ambition",
            ],
            "prevention_focus": [
                "safe", "secure", "protect", "avoid", "prevent", "careful",
                "responsible", "duty", "obligation", "vigilant",
            ],
        }
    
    @property
    def provider_name(self) -> str:
        return "psychological"
    
    @property
    def supported_models(self) -> List[EmbeddingModel]:
        return [
            EmbeddingModel.PSYCHOLOGICAL_BASE,
            EmbeddingModel.BRAND_PERSONALITY,
            EmbeddingModel.ADVERTISING_CREATIVE,
            EmbeddingModel.USER_BEHAVIOR,
        ]
    
    async def embed_single(
        self,
        text: str,
        model: EmbeddingModel,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """Generate psychological embedding for single text."""
        embeddings, metadata = await self.embed_batch([text], model)
        return embeddings[0], metadata
    
    async def embed_batch(
        self,
        texts: List[str],
        model: EmbeddingModel,
    ) -> Tuple[List[List[float]], Dict[str, Any]]:
        """Generate psychological embeddings for batch."""
        spec = get_model_spec(model)
        target_dim = spec.dimensions
        
        # Get base semantic embeddings
        base_embeddings, _ = await self._base_provider.embed_batch(
            texts, EmbeddingModel.ALL_MINILM_L6
        )
        
        # Apply psychological projection
        result_embeddings = []
        for i, (text, base_emb) in enumerate(zip(texts, base_embeddings)):
            psych_features = self._extract_psychological_features(text)
            projected = self._project_embedding(base_emb, psych_features, target_dim)
            result_embeddings.append(projected)
        
        return result_embeddings, {
            "model": model.value,
            "base_model": EmbeddingModel.ALL_MINILM_L6.value,
        }
    
    def _extract_psychological_features(self, text: str) -> Dict[str, float]:
        """Extract psychological features from text."""
        text_lower = text.lower()
        words = set(text_lower.split())
        
        features = {}
        for construct, keywords in self._construct_keywords.items():
            matches = sum(1 for kw in keywords if kw in words or kw in text_lower)
            features[construct] = min(matches / len(keywords), 1.0)
        
        return features
    
    def _project_embedding(
        self,
        base_embedding: List[float],
        psych_features: Dict[str, float],
        target_dim: int,
    ) -> List[float]:
        """
        Project base embedding into psychological space.
        
        Combines semantic representation with psychological feature signals.
        """
        import math
        
        base_dim = len(base_embedding)
        
        # Construct psychological feature vector
        psych_dim = len(psych_features)
        psych_vector = [psych_features.get(k, 0.0) for k in sorted(psych_features.keys())]
        
        # Combine base + psychological features
        combined = base_embedding + psych_vector
        
        # Project to target dimension using deterministic projection
        result = []
        for i in range(target_dim):
            # Mix of base embedding and psychological features
            base_idx = i % base_dim
            psych_idx = i % psych_dim
            
            base_weight = 0.7
            psych_weight = 0.3
            
            value = (
                base_weight * base_embedding[base_idx] +
                psych_weight * psych_vector[psych_idx]
            )
            
            # Add position-based modulation
            position_factor = math.sin(i * 0.1) * 0.1
            value += position_factor
            
            result.append(value)
        
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in result))
        if norm > 0:
            result = [x / norm for x in result]
        
        return result
    
    async def close(self) -> None:
        """Close base provider."""
        await self._base_provider.close()


# =============================================================================
# EMBEDDING GENERATOR (MAIN CLASS)
# =============================================================================

class EmbeddingGenerator:
    """
    Production-grade embedding generator with multi-provider support.
    
    Features:
    - Multiple provider backends (OpenAI, Cohere, Local, Custom)
    - Automatic provider selection based on model
    - Batch processing with chunking
    - Caching layer
    - Prometheus metrics
    - Fallback handling
    """
    
    def __init__(
        self,
        default_model: EmbeddingModel = EmbeddingModel.ALL_MINILM_L6,
        openai_api_key: Optional[str] = None,
        cohere_api_key: Optional[str] = None,
        enable_cache: bool = True,
        cache_ttl: int = 86400,
    ):
        self.default_model = default_model
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl
        
        # Initialize providers lazily
        self._providers: Dict[str, EmbeddingProvider] = {}
        self._openai_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self._cohere_key = cohere_api_key or os.environ.get("COHERE_API_KEY")
        
        # Simple in-memory cache (production: Redis)
        self._cache: Dict[str, Tuple[List[float], float]] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Settings
        self._settings = get_settings()
    
    def _get_provider(self, model: EmbeddingModel) -> EmbeddingProvider:
        """Get appropriate provider for model."""
        spec = get_model_spec(model)
        provider_name = spec.provider
        
        if provider_name not in self._providers:
            if provider_name == "openai":
                self._providers[provider_name] = OpenAIProvider(self._openai_key)
            elif provider_name == "cohere":
                self._providers[provider_name] = CohereProvider(self._cohere_key)
            elif provider_name == "local":
                self._providers[provider_name] = LocalProvider()
            elif provider_name == "custom":
                # Custom psychological models
                if "local" not in self._providers:
                    self._providers["local"] = LocalProvider()
                self._providers[provider_name] = PsychologicalProvider(
                    self._providers["local"]
                )
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
        
        return self._providers[provider_name]
    
    def _cache_key(self, text: str, model: EmbeddingModel) -> str:
        """Generate cache key for text+model."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"emb:{model.value}:{text_hash}"
    
    async def embed_text(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
    ) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            model: Model to use (defaults to default_model)
            
        Returns:
            Embedding vector
        """
        model = model or self.default_model
        
        # Check cache
        if self._enable_cache:
            cache_key = self._cache_key(text, model)
            if cache_key in self._cache:
                embedding, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    self._cache_hits += 1
                    return embedding
        
        self._cache_misses += 1
        
        # Get provider and embed
        provider = self._get_provider(model)
        
        start = time.perf_counter()
        try:
            embedding, metadata = await provider.embed_single(text, model)
            duration = time.perf_counter() - start
            
            # Record metrics
            EMBEDDING_REQUESTS.labels(
                provider=provider.provider_name,
                model=model.value,
                status="success",
            ).inc()
            EMBEDDING_LATENCY.labels(
                provider=provider.provider_name,
                model=model.value,
            ).observe(duration)
            
            if "tokens" in metadata:
                EMBEDDING_TOKENS.labels(
                    provider=provider.provider_name,
                    model=model.value,
                ).inc(metadata["tokens"])
            
            # Cache result
            if self._enable_cache:
                self._cache[cache_key] = (embedding, time.time())
            
            return embedding
            
        except Exception as e:
            EMBEDDING_REQUESTS.labels(
                provider=provider.provider_name,
                model=model.value,
                status="error",
            ).inc()
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    async def embed_batch(
        self,
        texts: List[str],
        model: Optional[EmbeddingModel] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: Texts to embed
            model: Model to use (defaults to default_model)
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = model or self.default_model
        BATCH_SIZE.observe(len(texts))
        
        # Check cache for each text
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        if self._enable_cache:
            for i, text in enumerate(texts):
                cache_key = self._cache_key(text, model)
                if cache_key in self._cache:
                    embedding, timestamp = self._cache[cache_key]
                    if time.time() - timestamp < self._cache_ttl:
                        results[i] = embedding
                        self._cache_hits += 1
                        continue
                
                texts_to_embed.append(text)
                indices_to_embed.append(i)
                self._cache_misses += 1
        else:
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))
        
        # If everything was cached, return early
        if not texts_to_embed:
            return results
        
        # Get provider and embed
        provider = self._get_provider(model)
        
        start = time.perf_counter()
        try:
            embeddings, metadata = await provider.embed_batch(texts_to_embed, model)
            duration = time.perf_counter() - start
            
            # Record metrics
            EMBEDDING_REQUESTS.labels(
                provider=provider.provider_name,
                model=model.value,
                status="success",
            ).inc(len(texts_to_embed))
            EMBEDDING_LATENCY.labels(
                provider=provider.provider_name,
                model=model.value,
            ).observe(duration / len(texts_to_embed))
            
            if "tokens" in metadata:
                EMBEDDING_TOKENS.labels(
                    provider=provider.provider_name,
                    model=model.value,
                ).inc(metadata["tokens"])
            
            # Fill in results and cache
            for i, (idx, text) in enumerate(zip(indices_to_embed, texts_to_embed)):
                results[idx] = embeddings[i]
                
                if self._enable_cache:
                    cache_key = self._cache_key(text, model)
                    self._cache[cache_key] = (embeddings[i], time.time())
            
            return results
            
        except Exception as e:
            EMBEDDING_REQUESTS.labels(
                provider=provider.provider_name,
                model=model.value,
                status="error",
            ).inc(len(texts_to_embed))
            logger.error(f"Batch embedding failed: {e}")
            raise
    
    async def embed_with_metadata(
        self,
        text: str,
        model: Optional[EmbeddingModel] = None,
    ) -> Tuple[List[float], Dict[str, Any]]:
        """
        Generate embedding with full metadata.
        
        Returns:
            Tuple of (embedding, metadata dict)
        """
        model = model or self.default_model
        spec = get_model_spec(model)
        
        start = time.perf_counter()
        embedding = await self.embed_text(text, model)
        duration = time.perf_counter() - start
        
        # Estimate tokens (rough approximation)
        token_estimate = len(text.split()) + len(text) // 4
        
        return embedding, {
            "model": model.value,
            "dimensions": spec.dimensions,
            "provider": spec.provider,
            "latency_ms": duration * 1000,
            "token_estimate": token_estimate,
            "normalized": spec.normalized,
        }
    
    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def close(self) -> None:
        """Close all providers."""
        for provider in self._providers.values():
            await provider.close()
