# =============================================================================
# Resonance Engineering — Redis Cache
# Location: adam/retargeting/resonance/resonance_cache.py
# =============================================================================

"""
Redis-backed resonance lookup cache.

Three cache tiers:
L1: Per-page resonance scores (page_url × mechanism → resonance_multiplier)
    TTL: 4 hours (pages change, but not minute-to-minute)

L2: Per-domain resonance scores (domain × mechanism → avg resonance)
    TTL: 24 hours (domain-level psychology is more stable)

L3: Mechanism ideal vectors (mechanism → 32-dim ideal vector)
    TTL: 7 days (updated by recalibration pipeline)
"""

import json
import logging
import time
from typing import Dict, Optional

import numpy as np

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    ResonanceScore,
    MINDSTATE_DIM_COUNT,
)

logger = logging.getLogger(__name__)


class ResonanceCache:
    """Redis-backed cache for resonance computations.

    Falls back to in-memory dict when Redis is unavailable.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory: Dict[str, Dict] = {}  # Fallback in-memory cache
        self._hits = 0
        self._misses = 0

    def get_page_resonance(
        self, url_pattern: str, mechanism: str
    ) -> Optional[float]:
        """L1: Get cached resonance multiplier for a page × mechanism."""
        key = f"resonance:page:{_hash_url(url_pattern)}:{mechanism}"
        val = self._get(key)
        if val is not None:
            self._hits += 1
            return float(val)
        self._misses += 1
        return None

    def set_page_resonance(
        self, url_pattern: str, mechanism: str, multiplier: float, ttl: int = 14400
    ) -> None:
        """L1: Cache resonance multiplier for a page × mechanism."""
        key = f"resonance:page:{_hash_url(url_pattern)}:{mechanism}"
        self._set(key, str(round(multiplier, 4)), ttl)

    def get_domain_resonance(
        self, domain: str, mechanism: str
    ) -> Optional[float]:
        """L2: Get cached domain-level resonance."""
        key = f"resonance:domain:{domain}:{mechanism}"
        val = self._get(key)
        if val is not None:
            self._hits += 1
            return float(val)
        self._misses += 1
        return None

    def set_domain_resonance(
        self, domain: str, mechanism: str, multiplier: float, ttl: int = 86400
    ) -> None:
        """L2: Cache domain-level resonance."""
        key = f"resonance:domain:{domain}:{mechanism}"
        self._set(key, str(round(multiplier, 4)), ttl)

    def get_mindstate_vector(self, url_pattern: str) -> Optional[np.ndarray]:
        """Get cached mindstate vector for a page."""
        key = f"resonance:mindstate:{_hash_url(url_pattern)}"
        val = self._get(key)
        if val is not None:
            self._hits += 1
            try:
                return np.array(json.loads(val))
            except (json.JSONDecodeError, TypeError):
                pass
        self._misses += 1
        return None

    def set_mindstate_vector(
        self, url_pattern: str, vector: np.ndarray, ttl: int = 14400
    ) -> None:
        """Cache mindstate vector for a page."""
        key = f"resonance:mindstate:{_hash_url(url_pattern)}"
        self._set(key, json.dumps(vector.tolist()), ttl)

    @property
    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(total, 1), 3),
            "cached_entries": len(self._memory),
        }

    # --- Storage layer ---

    def _get(self, key: str) -> Optional[str]:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass
        entry = self._memory.get(key)
        if entry and entry.get("expires", 0) > time.time():
            return entry["value"]
        return None

    def _set(self, key: str, value: str, ttl: int) -> None:
        if self._redis:
            try:
                self._redis.setex(key, ttl, value)
                return
            except Exception:
                pass
        self._memory[key] = {"value": value, "expires": time.time() + ttl}


def _hash_url(url: str) -> str:
    """Deterministic hash of URL for cache key."""
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]
