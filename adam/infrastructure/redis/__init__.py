# =============================================================================
# ADAM Redis Infrastructure
# Location: adam/infrastructure/redis/__init__.py
# =============================================================================

"""
REDIS CACHE INFRASTRUCTURE

ADAM-specific Redis patterns with hierarchical key conventions
designed for psychological intelligence workloads.

Key Domains:
- adam:profile:{user_id} - User psychological profiles
- adam:blackboard:{request_id} - Blackboard shared state
- adam:feature:{user_id}:{feature} - Cached features
- adam:decision:{decision_id} - Ad decisions
- adam:mechanism:{mechanism_id} - Mechanism state
- adam:session:{session_id} - Listening sessions
- adam:cache:* - General cache (with TTL)
"""

from adam.infrastructure.redis.cache import (
    ADAMRedisCache,
    CacheKeyBuilder,
    CacheDomain,
)

__all__ = [
    "ADAMRedisCache",
    "CacheKeyBuilder",
    "CacheDomain",
]
