# =============================================================================
# ADAM Enhancement #13: Prior Cache
# Location: adam/cold_start/cache/prior_cache.py
# =============================================================================

"""
Redis-based cache for cold start priors.

Caches:
- Population priors (long TTL)
- Demographic priors (medium TTL)
- Archetype profiles (long TTL)
- User tier cache (short TTL)
- Thompson Sampling posteriors (medium TTL)
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json
import logging

from adam.cold_start.models.enums import UserDataTier, ArchetypeID
from adam.cold_start.models.priors import PsychologicalPrior, BetaDistribution
from adam.cold_start.models.decisions import ColdStartDecision

logger = logging.getLogger(__name__)


class PriorCacheConfig:
    """Configuration for prior caching."""
    
    # TTLs in seconds
    POPULATION_PRIOR_TTL = 86400 * 7      # 7 days
    DEMOGRAPHIC_PRIOR_TTL = 86400         # 1 day
    ARCHETYPE_PROFILE_TTL = 86400 * 7     # 7 days
    USER_TIER_TTL = 300                   # 5 minutes
    THOMPSON_POSTERIOR_TTL = 3600         # 1 hour
    DECISION_TTL = 86400                  # 1 day (for learning)
    
    # Key prefixes
    PREFIX = "adam:coldstart"
    POPULATION_KEY = f"{PREFIX}:population"
    DEMOGRAPHIC_KEY = f"{PREFIX}:demographic"
    ARCHETYPE_KEY = f"{PREFIX}:archetype"
    USER_TIER_KEY = f"{PREFIX}:user:tier"
    THOMPSON_KEY = f"{PREFIX}:thompson"
    DECISION_KEY = f"{PREFIX}:decision"


class PriorCache:
    """
    Redis cache for cold start priors.
    
    Reduces latency by caching:
    - Pre-computed priors
    - User tier classifications
    - Thompson Sampling posteriors
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.config = PriorCacheConfig()
        
        # In-memory fallback when Redis unavailable
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        
        # Statistics
        self._hits = 0
        self._misses = 0
    
    async def get_population_prior(self) -> Optional[PsychologicalPrior]:
        """Get cached population prior."""
        data = await self._get(self.config.POPULATION_KEY)
        if data:
            return PsychologicalPrior.model_validate_json(data)
        return None
    
    async def set_population_prior(self, prior: PsychologicalPrior) -> None:
        """Cache population prior."""
        await self._set(
            self.config.POPULATION_KEY,
            prior.model_dump_json(),
            self.config.POPULATION_PRIOR_TTL
        )
    
    async def get_demographic_prior(
        self,
        age_bracket: Optional[str],
        gender: Optional[str]
    ) -> Optional[PsychologicalPrior]:
        """Get cached demographic prior."""
        key = f"{self.config.DEMOGRAPHIC_KEY}:{age_bracket or 'any'}:{gender or 'any'}"
        data = await self._get(key)
        if data:
            return PsychologicalPrior.model_validate_json(data)
        return None
    
    async def set_demographic_prior(
        self,
        prior: PsychologicalPrior,
        age_bracket: Optional[str],
        gender: Optional[str]
    ) -> None:
        """Cache demographic prior."""
        key = f"{self.config.DEMOGRAPHIC_KEY}:{age_bracket or 'any'}:{gender or 'any'}"
        await self._set(key, prior.model_dump_json(), self.config.DEMOGRAPHIC_PRIOR_TTL)
    
    async def get_archetype_profile(
        self,
        archetype_id: ArchetypeID
    ) -> Optional[PsychologicalPrior]:
        """Get cached archetype profile."""
        key = f"{self.config.ARCHETYPE_KEY}:{archetype_id.value}"
        data = await self._get(key)
        if data:
            return PsychologicalPrior.model_validate_json(data)
        return None
    
    async def set_archetype_profile(
        self,
        archetype_id: ArchetypeID,
        profile: PsychologicalPrior
    ) -> None:
        """Cache archetype profile."""
        key = f"{self.config.ARCHETYPE_KEY}:{archetype_id.value}"
        await self._set(key, profile.model_dump_json(), self.config.ARCHETYPE_PROFILE_TTL)
    
    async def get_user_tier(self, user_id: str) -> Optional[UserDataTier]:
        """Get cached user tier."""
        key = f"{self.config.USER_TIER_KEY}:{user_id}"
        data = await self._get(key)
        if data:
            return UserDataTier(data)
        return None
    
    async def set_user_tier(self, user_id: str, tier: UserDataTier) -> None:
        """Cache user tier."""
        key = f"{self.config.USER_TIER_KEY}:{user_id}"
        await self._set(key, tier.value, self.config.USER_TIER_TTL)
    
    async def get_thompson_posterior(
        self,
        archetype_id: ArchetypeID,
        mechanism: str
    ) -> Optional[BetaDistribution]:
        """Get cached Thompson posterior."""
        key = f"{self.config.THOMPSON_KEY}:{archetype_id.value}:{mechanism}"
        data = await self._get(key)
        if data:
            return BetaDistribution.model_validate_json(data)
        return None
    
    async def set_thompson_posterior(
        self,
        archetype_id: ArchetypeID,
        mechanism: str,
        posterior: BetaDistribution
    ) -> None:
        """Cache Thompson posterior."""
        key = f"{self.config.THOMPSON_KEY}:{archetype_id.value}:{mechanism}"
        await self._set(key, posterior.model_dump_json(), self.config.THOMPSON_POSTERIOR_TTL)
    
    async def get_decision(self, request_id: str) -> Optional[ColdStartDecision]:
        """Get cached decision for learning."""
        key = f"{self.config.DECISION_KEY}:{request_id}"
        data = await self._get(key)
        if data:
            return ColdStartDecision.model_validate_json(data)
        return None
    
    async def set_decision(self, decision: ColdStartDecision) -> None:
        """Cache decision for learning."""
        key = f"{self.config.DECISION_KEY}:{decision.request_id}"
        await self._set(key, decision.model_dump_json(), self.config.DECISION_TTL)
    
    async def _get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        # Try Redis first
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self._hits += 1
                    return value
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry > datetime.utcnow():
                self._hits += 1
                return value
            else:
                del self._memory_cache[key]
        
        self._misses += 1
        return None
    
    async def _set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache."""
        # Try Redis first
        if self.redis:
            try:
                await self.redis.setex(key, ttl, value)
                return
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory
        expiry = datetime.utcnow() + timedelta(seconds=ttl)
        self._memory_cache[key] = (value, expiry)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, total),
            "memory_cache_size": len(self._memory_cache),
        }


# Singleton instance
_cache: Optional[PriorCache] = None


def get_prior_cache(redis_client=None) -> PriorCache:
    """Get singleton prior cache."""
    global _cache
    if _cache is None:
        _cache = PriorCache(redis_client)
    return _cache
