# =============================================================================
# ADAM Redis Cache Patterns
# Location: adam/infrastructure/redis/cache.py
# =============================================================================

"""
ADAM REDIS CACHE

Provides high-level caching abstractions for ADAM components
with consistent key conventions, TTL management, and atomic operations.

Key Design Principles:
1. Hierarchical keys for pattern-based operations
2. Domain-specific TTLs
3. Atomic operations via Lua scripts
4. Consistent serialization (JSON with type hints)
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# KEY DOMAINS AND TTL CONFIGURATION
# =============================================================================

class CacheDomain(str, Enum):
    """
    Cache key domains with semantic meaning.
    
    Each domain has specific characteristics:
    - Different TTLs based on data volatility
    - Different access patterns (read-heavy vs write-heavy)
    - Different eviction priorities
    """
    
    # Core user data
    PROFILE = "profile"           # User psychological profiles
    FEATURE = "feature"           # Computed features
    ARCHETYPE = "archetype"       # Matched archetypes
    
    # Request processing
    BLACKBOARD = "blackboard"     # Shared state for request
    DECISION = "decision"         # Ad decision state
    REQUEST = "request"           # Request metadata
    
    # Learning state
    MECHANISM = "mechanism"       # Mechanism state/priors
    SIGNAL = "signal"             # Pending learning signals
    
    # Session data
    SESSION = "session"           # Listening sessions
    EVENT = "event"               # Session events
    
    # Platform-specific
    IHEART = "iheart"             # iHeart platform data
    AMAZON = "amazon"             # Amazon corpus data
    WPP = "wpp"                   # WPP integration data
    
    # General cache
    CACHE = "cache"               # General purpose cache


# TTL configurations (in seconds)
DOMAIN_TTLS: Dict[CacheDomain, int] = {
    # Core user data - longer TTL, less volatile
    CacheDomain.PROFILE: 3600 * 4,        # 4 hours
    CacheDomain.FEATURE: 3600,            # 1 hour
    CacheDomain.ARCHETYPE: 3600 * 24,     # 24 hours
    
    # Request processing - short TTL
    CacheDomain.BLACKBOARD: 300,          # 5 minutes
    CacheDomain.DECISION: 600,            # 10 minutes
    CacheDomain.REQUEST: 300,             # 5 minutes
    
    # Learning state - medium TTL
    CacheDomain.MECHANISM: 3600,          # 1 hour
    CacheDomain.SIGNAL: 60,               # 1 minute (processed quickly)
    
    # Session data - medium TTL
    CacheDomain.SESSION: 3600 * 2,        # 2 hours
    CacheDomain.EVENT: 1800,              # 30 minutes
    
    # Platform-specific
    CacheDomain.IHEART: 1800,             # 30 minutes
    CacheDomain.AMAZON: 3600 * 24,        # 24 hours (stable corpus data)
    CacheDomain.WPP: 1800,                # 30 minutes
    
    # General cache
    CacheDomain.CACHE: 3600,              # 1 hour default
}


# =============================================================================
# KEY BUILDER
# =============================================================================

class CacheKeyBuilder:
    """
    Builds hierarchical Redis keys for ADAM.
    
    Key format: adam:{domain}:{component}:{id}[:subkey]
    
    Examples:
    - adam:profile:user:u_12345
    - adam:blackboard:req:r_abc123:reasoning_state
    - adam:feature:user:u_12345:big_five
    - adam:decision:dec:d_xyz789:outcome
    """
    
    PREFIX = "adam"
    
    @classmethod
    def profile(cls, user_id: str) -> str:
        """Build user profile key."""
        return f"{cls.PREFIX}:{CacheDomain.PROFILE}:user:{user_id}"
    
    @classmethod
    def feature(cls, user_id: str, feature_name: str) -> str:
        """Build feature cache key."""
        return f"{cls.PREFIX}:{CacheDomain.FEATURE}:user:{user_id}:{feature_name}"
    
    @classmethod
    def archetype(cls, user_id: str) -> str:
        """Build archetype key."""
        return f"{cls.PREFIX}:{CacheDomain.ARCHETYPE}:user:{user_id}"
    
    @classmethod
    def blackboard(cls, request_id: str, subkey: Optional[str] = None) -> str:
        """Build blackboard state key."""
        key = f"{cls.PREFIX}:{CacheDomain.BLACKBOARD}:req:{request_id}"
        if subkey:
            key = f"{key}:{subkey}"
        return key
    
    @classmethod
    def decision(cls, decision_id: str, subkey: Optional[str] = None) -> str:
        """Build decision key."""
        key = f"{cls.PREFIX}:{CacheDomain.DECISION}:dec:{decision_id}"
        if subkey:
            key = f"{key}:{subkey}"
        return key
    
    @classmethod
    def mechanism(cls, mechanism_id: str, subkey: Optional[str] = None) -> str:
        """Build mechanism state key."""
        key = f"{cls.PREFIX}:{CacheDomain.MECHANISM}:mech:{mechanism_id}"
        if subkey:
            key = f"{key}:{subkey}"
        return key
    
    @classmethod
    def session(cls, session_id: str, subkey: Optional[str] = None) -> str:
        """Build session key."""
        key = f"{cls.PREFIX}:{CacheDomain.SESSION}:sess:{session_id}"
        if subkey:
            key = f"{key}:{subkey}"
        return key
    
    @classmethod
    def iheart_station(cls, station_id: str) -> str:
        """Build iHeart station key."""
        return f"{cls.PREFIX}:{CacheDomain.IHEART}:station:{station_id}"
    
    @classmethod
    def iheart_user_prefs(cls, user_id: str) -> str:
        """Build iHeart user preferences key."""
        return f"{cls.PREFIX}:{CacheDomain.IHEART}:user_prefs:{user_id}"
    
    @classmethod
    def amazon_user(cls, amazon_user_id: str) -> str:
        """Build Amazon user profile key."""
        return f"{cls.PREFIX}:{CacheDomain.AMAZON}:user:{amazon_user_id}"
    
    @classmethod
    def amazon_archetype(cls, archetype_id: str) -> str:
        """Build Amazon archetype key."""
        return f"{cls.PREFIX}:{CacheDomain.AMAZON}:archetype:{archetype_id}"
    
    @classmethod
    def cache(cls, namespace: str, key: str) -> str:
        """Build general cache key."""
        return f"{cls.PREFIX}:{CacheDomain.CACHE}:{namespace}:{key}"
    
    @classmethod
    def meta_learner_posteriors(cls) -> str:
        """Build meta-learner posterior state key."""
        return f"{cls.PREFIX}:{CacheDomain.FEATURE}:meta_learner:posteriors"
    
    @classmethod
    def meta_learner_context(cls, user_id: str) -> str:
        """Build meta-learner user context key."""
        return f"{cls.PREFIX}:{CacheDomain.FEATURE}:meta_learner:context:{user_id}"
    
    @classmethod
    def pattern(cls, domain: CacheDomain, pattern: str = "*") -> str:
        """Build a pattern for key scanning."""
        return f"{cls.PREFIX}:{domain}:{pattern}"


# =============================================================================
# ADAM REDIS CACHE
# =============================================================================

class ADAMRedisCache:
    """
    High-level Redis cache for ADAM.
    
    Features:
    - Automatic TTL management per domain
    - Pydantic model serialization
    - Atomic increment/decrement operations
    - Pattern-based key operations
    - Metrics integration
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._metrics_enabled = True
    
    # -------------------------------------------------------------------------
    # BASIC OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get(
        self,
        key: str,
        model_class: Optional[type[T]] = None
    ) -> Optional[Union[Dict, T]]:
        """
        Get a value from cache.
        
        Args:
            key: Redis key
            model_class: Optional Pydantic model to deserialize into
            
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            data = json.loads(value)
            
            if model_class:
                return model_class.model_validate(data)
            return data
            
        except Exception as e:
            logger.error(f"Cache get failed for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Union[Dict, BaseModel],
        ttl: Optional[int] = None,
        domain: Optional[CacheDomain] = None,
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Redis key
            value: Value to cache (dict or Pydantic model)
            ttl: TTL in seconds (overrides domain default)
            domain: Cache domain for default TTL
            
        Returns:
            True if successful
        """
        try:
            # Serialize value
            if isinstance(value, BaseModel):
                data = value.model_dump(mode="json")
            else:
                data = value
            
            json_value = json.dumps(data, default=str)
            
            # Determine TTL
            if ttl is None and domain:
                ttl = DOMAIN_TTLS.get(domain, DOMAIN_TTLS[CacheDomain.CACHE])
            
            if ttl:
                await self.redis.setex(key, ttl, json_value)
            else:
                await self.redis.set(key, json_value)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set failed for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete failed for {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists check failed for {key}: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # DOMAIN-SPECIFIC OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_profile(self, user_id: str, model_class: Optional[type[T]] = None):
        """Get user profile from cache."""
        key = CacheKeyBuilder.profile(user_id)
        return await self.get(key, model_class)
    
    async def set_profile(self, user_id: str, profile: Union[Dict, BaseModel]) -> bool:
        """Cache user profile."""
        key = CacheKeyBuilder.profile(user_id)
        return await self.set(key, profile, domain=CacheDomain.PROFILE)
    
    async def get_blackboard(self, request_id: str, subkey: Optional[str] = None):
        """Get blackboard state."""
        key = CacheKeyBuilder.blackboard(request_id, subkey)
        return await self.get(key)
    
    async def set_blackboard(
        self,
        request_id: str,
        state: Dict,
        subkey: Optional[str] = None
    ) -> bool:
        """Set blackboard state."""
        key = CacheKeyBuilder.blackboard(request_id, subkey)
        return await self.set(key, state, domain=CacheDomain.BLACKBOARD)
    
    async def get_feature(self, user_id: str, feature_name: str):
        """Get cached feature."""
        key = CacheKeyBuilder.feature(user_id, feature_name)
        return await self.get(key)
    
    async def set_feature(
        self,
        user_id: str,
        feature_name: str,
        value: Union[Dict, BaseModel]
    ) -> bool:
        """Cache feature value."""
        key = CacheKeyBuilder.feature(user_id, feature_name)
        return await self.set(key, value, domain=CacheDomain.FEATURE)
    
    # -------------------------------------------------------------------------
    # ATOMIC OPERATIONS
    # -------------------------------------------------------------------------
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter."""
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed for {key}: {e}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Atomically decrement a counter."""
        try:
            return await self.redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"Cache decrement failed for {key}: {e}")
            return 0
    
    async def increment_float(self, key: str, amount: float = 1.0) -> float:
        """Atomically increment a float counter."""
        try:
            return await self.redis.incrbyfloat(key, amount)
        except Exception as e:
            logger.error(f"Cache increment_float failed for {key}: {e}")
            return 0.0
    
    # -------------------------------------------------------------------------
    # HASH OPERATIONS (for complex objects)
    # -------------------------------------------------------------------------
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        try:
            return await self.redis.hget(key, field)
        except Exception as e:
            logger.error(f"Cache hget failed for {key}:{field}: {e}")
            return None
    
    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set hash field."""
        try:
            await self.redis.hset(key, field, value)
            return True
        except Exception as e:
            logger.error(f"Cache hset failed for {key}:{field}: {e}")
            return False
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        try:
            return await self.redis.hgetall(key)
        except Exception as e:
            logger.error(f"Cache hgetall failed for {key}: {e}")
            return {}
    
    async def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        """Set multiple hash fields."""
        try:
            await self.redis.hset(key, mapping=mapping)
            return True
        except Exception as e:
            logger.error(f"Cache hmset failed for {key}: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # PATTERN OPERATIONS
    # -------------------------------------------------------------------------
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            deleted = 0
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
                deleted += 1
            return deleted
        except Exception as e:
            logger.error(f"Cache delete_pattern failed for {pattern}: {e}")
            return 0
    
    async def count_pattern(self, pattern: str) -> int:
        """Count keys matching pattern."""
        try:
            count = 0
            async for _ in self.redis.scan_iter(match=pattern):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Cache count_pattern failed for {pattern}: {e}")
            return 0
    
    # -------------------------------------------------------------------------
    # TTL MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        try:
            return await self.redis.expire(key, ttl)
        except Exception as e:
            logger.error(f"Cache expire failed for {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache ttl failed for {key}: {e}")
            return -1
    
    # -------------------------------------------------------------------------
    # PIPELINE OPERATIONS
    # -------------------------------------------------------------------------
    
    async def mget(self, keys: List[str]) -> List[Optional[Dict]]:
        """Get multiple keys at once."""
        try:
            values = await self.redis.mget(keys)
            results = []
            for v in values:
                if v is None:
                    results.append(None)
                else:
                    results.append(json.loads(v))
            return results
        except Exception as e:
            logger.error(f"Cache mget failed: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, Union[Dict, BaseModel]]) -> bool:
        """Set multiple keys at once."""
        try:
            serialized = {}
            for k, v in mapping.items():
                if isinstance(v, BaseModel):
                    serialized[k] = json.dumps(v.model_dump(mode="json"), default=str)
                else:
                    serialized[k] = json.dumps(v, default=str)
            
            await self.redis.mset(serialized)
            return True
        except Exception as e:
            logger.error(f"Cache mset failed: {e}")
            return False
