# =============================================================================
# ADAM Behavioral Analytics: Cache Extension
# Location: adam/behavioral_analytics/extensions/cache_extension.py
# =============================================================================

"""
CACHE EXTENSION FOR BEHAVIORAL ANALYTICS

Extends the existing Redis Cache (#31) infrastructure with
behavioral-specific caching for:
- Session state
- Behavioral features
- Psychological inferences
- User behavioral profiles
- Knowledge cache
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BehavioralCacheDomain(str, Enum):
    """
    Behavioral cache key domains.
    
    These extend the base CacheDomain with behavioral-specific domains.
    """
    # Session data
    BEHAVIORAL_SESSION = "behavioral_session"     # Active session state
    BEHAVIORAL_FEATURES = "behavioral_features"   # Computed features
    BEHAVIORAL_INFERENCE = "behavioral_inference"  # Psychological inferences
    
    # User profiles
    BEHAVIORAL_PROFILE = "behavioral_profile"     # Aggregated behavioral profile
    BEHAVIORAL_BASELINE = "behavioral_baseline"   # Per-user signal baselines
    
    # Knowledge
    BEHAVIORAL_KNOWLEDGE = "behavioral_knowledge"  # Cached knowledge items
    BEHAVIORAL_HYPOTHESIS = "behavioral_hypothesis"  # Active hypotheses


# TTL configurations for behavioral domains (in seconds)
BEHAVIORAL_TTLS: Dict[BehavioralCacheDomain, int] = {
    # Session data - short TTL (active sessions)
    BehavioralCacheDomain.BEHAVIORAL_SESSION: 1800,     # 30 minutes
    BehavioralCacheDomain.BEHAVIORAL_FEATURES: 900,     # 15 minutes
    BehavioralCacheDomain.BEHAVIORAL_INFERENCE: 900,    # 15 minutes
    
    # User profiles - longer TTL
    BehavioralCacheDomain.BEHAVIORAL_PROFILE: 7200,     # 2 hours
    BehavioralCacheDomain.BEHAVIORAL_BASELINE: 86400,   # 24 hours
    
    # Knowledge - long TTL (stable)
    BehavioralCacheDomain.BEHAVIORAL_KNOWLEDGE: 43200,  # 12 hours
    BehavioralCacheDomain.BEHAVIORAL_HYPOTHESIS: 3600,  # 1 hour
}


class BehavioralCacheKeyBuilder:
    """
    Builds hierarchical Redis keys for behavioral analytics.
    
    Key format: adam:behavioral:{domain}:{id}[:subkey]
    
    Examples:
    - adam:behavioral:session:sess_12345
    - adam:behavioral:profile:user:u_abc123
    - adam:behavioral:features:sess_12345:touch
    - adam:behavioral:inference:sess_12345
    """
    
    PREFIX = "adam:behavioral"
    
    @classmethod
    def session(cls, session_id: str, subkey: Optional[str] = None) -> str:
        """Build behavioral session key."""
        key = f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_SESSION}:{session_id}"
        if subkey:
            key = f"{key}:{subkey}"
        return key
    
    @classmethod
    def features(cls, session_id: str, feature_type: Optional[str] = None) -> str:
        """Build behavioral features key."""
        key = f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_FEATURES}:{session_id}"
        if feature_type:
            key = f"{key}:{feature_type}"
        return key
    
    @classmethod
    def inference(cls, session_id: str) -> str:
        """Build inference key."""
        return f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_INFERENCE}:{session_id}"
    
    @classmethod
    def profile(cls, user_id: str) -> str:
        """Build user behavioral profile key."""
        return f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_PROFILE}:user:{user_id}"
    
    @classmethod
    def baseline(cls, user_id: str, signal_type: Optional[str] = None) -> str:
        """Build user signal baseline key."""
        key = f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_BASELINE}:user:{user_id}"
        if signal_type:
            key = f"{key}:{signal_type}"
        return key
    
    @classmethod
    def knowledge(cls, construct: str) -> str:
        """Build knowledge cache key."""
        return f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_KNOWLEDGE}:construct:{construct}"
    
    @classmethod
    def hypothesis(cls, hypothesis_id: str) -> str:
        """Build hypothesis cache key."""
        return f"{cls.PREFIX}:{BehavioralCacheDomain.BEHAVIORAL_HYPOTHESIS}:{hypothesis_id}"
    
    @classmethod
    def pattern(cls, domain: BehavioralCacheDomain, pattern: str = "*") -> str:
        """Build a pattern for key scanning."""
        return f"{cls.PREFIX}:{domain}:{pattern}"


class BehavioralCache:
    """
    Behavioral analytics cache.
    
    Extends ADAMRedisCache with behavioral-specific operations.
    
    Features:
    - Session state caching for fast inference
    - Feature vector caching
    - User baseline management
    - Knowledge cache with TTL
    """
    
    def __init__(self, redis_cache):
        """
        Initialize behavioral cache.
        
        Args:
            redis_cache: Instance of ADAMRedisCache
        """
        self._cache = redis_cache
    
    # -------------------------------------------------------------------------
    # SESSION OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_session(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached session state."""
        key = BehavioralCacheKeyBuilder.session(session_id)
        return await self._cache.get(key)
    
    async def set_session(
        self,
        session_id: str,
        session_data: Union[Dict, BaseModel],
    ) -> bool:
        """Cache session state."""
        key = BehavioralCacheKeyBuilder.session(session_id)
        return await self._cache.set(
            key,
            session_data,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_SESSION]
        )
    
    async def update_session_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> bool:
        """Append event to session's event list."""
        key = BehavioralCacheKeyBuilder.session(session_id, f"events:{event_type}")
        # Use Redis list for event accumulation
        try:
            import json
            await self._cache.redis.rpush(key, json.dumps(event_data, default=str))
            await self._cache.redis.expire(
                key,
                BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_SESSION]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update session event: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # FEATURE OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_features(
        self,
        session_id: str,
        feature_type: Optional[str] = None,
    ) -> Optional[Dict[str, float]]:
        """Get cached features for a session."""
        key = BehavioralCacheKeyBuilder.features(session_id, feature_type)
        return await self._cache.get(key)
    
    async def set_features(
        self,
        session_id: str,
        features: Dict[str, float],
        feature_type: Optional[str] = None,
    ) -> bool:
        """Cache computed features."""
        key = BehavioralCacheKeyBuilder.features(session_id, feature_type)
        return await self._cache.set(
            key,
            features,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_FEATURES]
        )
    
    # -------------------------------------------------------------------------
    # INFERENCE OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_inference(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached psychological inference."""
        key = BehavioralCacheKeyBuilder.inference(session_id)
        return await self._cache.get(key)
    
    async def set_inference(
        self,
        session_id: str,
        inference: Union[Dict, BaseModel],
    ) -> bool:
        """Cache psychological inference."""
        key = BehavioralCacheKeyBuilder.inference(session_id)
        return await self._cache.set(
            key,
            inference,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_INFERENCE]
        )
    
    # -------------------------------------------------------------------------
    # PROFILE OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_profile(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached behavioral profile for user."""
        key = BehavioralCacheKeyBuilder.profile(user_id)
        return await self._cache.get(key)
    
    async def set_profile(
        self,
        user_id: str,
        profile: Union[Dict, BaseModel],
    ) -> bool:
        """Cache behavioral profile."""
        key = BehavioralCacheKeyBuilder.profile(user_id)
        return await self._cache.set(
            key,
            profile,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_PROFILE]
        )
    
    async def get_baseline(
        self,
        user_id: str,
        signal_type: Optional[str] = None,
    ) -> Optional[Dict[str, float]]:
        """Get user's signal baseline."""
        key = BehavioralCacheKeyBuilder.baseline(user_id, signal_type)
        return await self._cache.get(key)
    
    async def set_baseline(
        self,
        user_id: str,
        baseline: Dict[str, float],
        signal_type: Optional[str] = None,
    ) -> bool:
        """Cache user's signal baseline."""
        key = BehavioralCacheKeyBuilder.baseline(user_id, signal_type)
        return await self._cache.set(
            key,
            baseline,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_BASELINE]
        )
    
    async def update_baseline(
        self,
        user_id: str,
        new_values: Dict[str, float],
        alpha: float = 0.1,
        signal_type: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Update baseline with exponential moving average.
        
        Args:
            user_id: User identifier
            new_values: New signal values
            alpha: Learning rate for EMA (default 0.1)
            signal_type: Optional signal type filter
            
        Returns:
            Updated baseline
        """
        current = await self.get_baseline(user_id, signal_type) or {}
        
        updated = {}
        for key, value in new_values.items():
            if key in current:
                # EMA update
                updated[key] = (1 - alpha) * current[key] + alpha * value
            else:
                # Initialize
                updated[key] = value
        
        # Preserve keys not in new_values
        for key in current:
            if key not in updated:
                updated[key] = current[key]
        
        await self.set_baseline(user_id, updated, signal_type)
        return updated
    
    # -------------------------------------------------------------------------
    # KNOWLEDGE OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_knowledge(
        self,
        construct: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached knowledge for a construct."""
        key = BehavioralCacheKeyBuilder.knowledge(construct)
        return await self._cache.get(key)
    
    async def set_knowledge(
        self,
        construct: str,
        knowledge: List[Dict[str, Any]],
    ) -> bool:
        """Cache knowledge for a construct."""
        key = BehavioralCacheKeyBuilder.knowledge(construct)
        return await self._cache.set(
            key,
            knowledge,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_KNOWLEDGE]
        )
    
    async def invalidate_knowledge(self, construct: Optional[str] = None) -> int:
        """Invalidate cached knowledge."""
        if construct:
            key = BehavioralCacheKeyBuilder.knowledge(construct)
            await self._cache.delete(key)
            return 1
        else:
            pattern = BehavioralCacheKeyBuilder.pattern(
                BehavioralCacheDomain.BEHAVIORAL_KNOWLEDGE
            )
            return await self._cache.delete_pattern(pattern)
    
    # -------------------------------------------------------------------------
    # HYPOTHESIS OPERATIONS
    # -------------------------------------------------------------------------
    
    async def get_hypothesis(
        self,
        hypothesis_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached hypothesis."""
        key = BehavioralCacheKeyBuilder.hypothesis(hypothesis_id)
        return await self._cache.get(key)
    
    async def set_hypothesis(
        self,
        hypothesis_id: str,
        hypothesis: Union[Dict, BaseModel],
    ) -> bool:
        """Cache hypothesis."""
        key = BehavioralCacheKeyBuilder.hypothesis(hypothesis_id)
        return await self._cache.set(
            key,
            hypothesis,
            ttl=BEHAVIORAL_TTLS[BehavioralCacheDomain.BEHAVIORAL_HYPOTHESIS]
        )
    
    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    
    async def cleanup_session(self, session_id: str) -> int:
        """Clean up all cache entries for a session."""
        patterns = [
            BehavioralCacheKeyBuilder.session(session_id, "*"),
            BehavioralCacheKeyBuilder.features(session_id, "*"),
            BehavioralCacheKeyBuilder.inference(session_id),
        ]
        
        deleted = 0
        for pattern in patterns:
            deleted += await self._cache.delete_pattern(pattern)
        
        return deleted
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for behavioral domains."""
        stats = {}
        
        for domain in BehavioralCacheDomain:
            pattern = BehavioralCacheKeyBuilder.pattern(domain)
            count = await self._cache.count_pattern(pattern)
            stats[domain.value] = count
        
        return stats


# Factory function
def get_behavioral_cache(redis_cache) -> BehavioralCache:
    """Create behavioral cache instance."""
    return BehavioralCache(redis_cache)
