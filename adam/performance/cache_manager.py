# =============================================================================
# ADAM Multi-Level Cache Manager
# Location: adam/performance/cache_manager.py
# =============================================================================

"""
MULTI-LEVEL CACHE MANAGER

L1: In-memory (request-scoped)
L2: Redis (shared, hot data)
L3: Neo4j (persistent, cold data)

Optimized for sub-100ms latency with cache warming.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# METRICS
# =============================================================================

CACHE_HITS = Counter(
    "adam_cache_hits_total",
    "Cache hits",
    ["level", "key_type"],
)

CACHE_MISSES = Counter(
    "adam_cache_misses_total",
    "Cache misses",
    ["level", "key_type"],
)

CACHE_LATENCY = Histogram(
    "adam_cache_latency_ms",
    "Cache operation latency",
    ["level", "operation"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 25, 50],
)


# =============================================================================
# L1 CACHE (IN-MEMORY, REQUEST-SCOPED)
# =============================================================================

class L1Cache:
    """
    L1 in-memory cache with LRU eviction.
    
    Very fast, small capacity, request-scoped.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get from L1 cache."""
        start = time.perf_counter()
        
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            CACHE_HITS.labels(level="L1", key_type=self._key_type(key)).inc()
            CACHE_LATENCY.labels(level="L1", operation="get").observe(
                (time.perf_counter() - start) * 1000
            )
            return self._cache[key]
        
        self._misses += 1
        CACHE_MISSES.labels(level="L1", key_type=self._key_type(key)).inc()
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set in L1 cache with LRU eviction."""
        start = time.perf_counter()
        
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                # Evict oldest
                self._cache.popitem(last=False)
            
        self._cache[key] = value
        
        CACHE_LATENCY.labels(level="L1", operation="set").observe(
            (time.perf_counter() - start) * 1000
        )
    
    def invalidate(self, key: str) -> None:
        """Invalidate a key."""
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
    
    def _key_type(self, key: str) -> str:
        """Extract key type from key."""
        if ":" in key:
            return key.split(":")[0]
        return "unknown"
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


# =============================================================================
# MULTI-LEVEL CACHE MANAGER
# =============================================================================

class CacheConfig(BaseModel):
    """Cache configuration."""
    
    l1_max_size: int = Field(default=1000)
    l1_ttl_seconds: int = Field(default=60)
    
    l2_ttl_seconds: int = Field(default=3600)
    
    enable_write_through: bool = Field(default=True)
    enable_read_through: bool = Field(default=True)
    
    # Warming
    enable_warming: bool = Field(default=True)
    warming_batch_size: int = Field(default=100)


class MultiLevelCacheManager:
    """
    Multi-level cache with L1 (memory), L2 (Redis), L3 (Neo4j).
    """
    
    def __init__(
        self,
        redis_cache=None,
        graph_service=None,
        config: Optional[CacheConfig] = None,
    ):
        self.config = config or CacheConfig()
        self.l1 = L1Cache(max_size=self.config.l1_max_size)
        self.redis = redis_cache
        self.graph = graph_service
    
    async def get(
        self,
        key: str,
        key_type: str = "generic",
    ) -> Optional[Any]:
        """
        Get value with cache hierarchy.
        
        Checks L1 → L2 → L3, populating higher levels on miss.
        """
        
        # L1 check
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # L2 check
        if self.redis:
            start = time.perf_counter()
            value = await self.redis.get(key)
            CACHE_LATENCY.labels(level="L2", operation="get").observe(
                (time.perf_counter() - start) * 1000
            )
            
            if value is not None:
                CACHE_HITS.labels(level="L2", key_type=key_type).inc()
                # Populate L1
                self.l1.set(key, value)
                return value
            
            CACHE_MISSES.labels(level="L2", key_type=key_type).inc()
        
        # L3 check (read-through)
        if self.config.enable_read_through and self.graph:
            value = await self._read_from_graph(key, key_type)
            
            if value is not None:
                CACHE_HITS.labels(level="L3", key_type=key_type).inc()
                # Populate L1 and L2
                self.l1.set(key, value)
                if self.redis:
                    await self.redis.set(
                        key, value, 
                        ttl=self.config.l2_ttl_seconds
                    )
                return value
            
            CACHE_MISSES.labels(level="L3", key_type=key_type).inc()
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        key_type: str = "generic",
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache hierarchy.
        
        Writes to L1 immediately, L2 async.
        """
        
        # L1 always
        self.l1.set(key, value)
        
        # L2 
        if self.redis:
            await self.redis.set(
                key, value,
                ttl=ttl or self.config.l2_ttl_seconds,
            )
        
        # L3 write-through
        if self.config.enable_write_through and self.graph:
            asyncio.create_task(
                self._write_to_graph(key, value, key_type)
            )
    
    async def invalidate(
        self,
        key: str,
    ) -> None:
        """Invalidate a key across all levels."""
        
        self.l1.invalidate(key)
        
        if self.redis:
            await self.redis.delete(key)
    
    async def warm(
        self,
        keys: List[str],
        key_type: str = "generic",
    ) -> int:
        """
        Warm cache with keys from L3.
        
        Returns number of keys warmed.
        """
        if not self.config.enable_warming:
            return 0
        
        warmed = 0
        
        # Batch fetch from graph
        for i in range(0, len(keys), self.config.warming_batch_size):
            batch = keys[i:i + self.config.warming_batch_size]
            
            for key in batch:
                value = await self._read_from_graph(key, key_type)
                if value is not None:
                    self.l1.set(key, value)
                    if self.redis:
                        await self.redis.set(
                            key, value,
                            ttl=self.config.l2_ttl_seconds,
                        )
                    warmed += 1
        
        logger.info(f"Warmed {warmed}/{len(keys)} keys of type {key_type}")
        return warmed
    
    async def warm_user(self, user_id: str) -> int:
        """Warm cache for a specific user."""
        keys = [
            f"profile:{user_id}",
            f"mechanisms:{user_id}",
            f"journey:{user_id}",
            f"cold_start:{user_id}",
        ]
        return await self.warm(keys, "user")
    
    async def _read_from_graph(
        self,
        key: str,
        key_type: str,
    ) -> Optional[Any]:
        """Read from Neo4j graph."""
        if not self.graph:
            return None
        
        # Parse key to determine query
        if key.startswith("profile:"):
            user_id = key.split(":")[1]
            return await self.graph.get_user_profile(user_id)
        
        if key.startswith("mechanisms:"):
            user_id = key.split(":")[1]
            return await self.graph.get_mechanism_effectiveness(user_id)
        
        return None
    
    async def _write_to_graph(
        self,
        key: str,
        value: Any,
        key_type: str,
    ) -> None:
        """Write to Neo4j graph (async, fire-and-forget)."""
        if not self.graph:
            return
        
        try:
            if key.startswith("profile:"):
                user_id = key.split(":")[1]
                await self.graph.update_user_profile(user_id, value)
        except Exception as e:
            logger.error(f"Failed to write to graph: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "l1_size": len(self.l1._cache),
            "l1_max_size": self.l1.max_size,
            "l1_hit_rate": self.l1.hit_rate,
            "l1_hits": self.l1._hits,
            "l1_misses": self.l1._misses,
        }
