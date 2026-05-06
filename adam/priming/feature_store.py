"""Page-priming Feature Store cascade (directive §S3.3).

L1 in-process LRU → L2 Redis (optional) → L3 Memcached (optional)
→ cold-miss neutral signature fallback. Lookup key is `url_hash`
(SHA-256 hex digest, see `pipeline.url_to_hash`).

Per Enhancement #31 cascade pattern: L1 absorbs hot-set lookups in-
process for sub-microsecond latency; L2 Redis is the multi-process
shared cache for warm-set lookups; L3 Memcached is the fall-through
backstop. Cold-miss path emits `neutral_signature(url_hash)` with
all confidence_per_dimension floored at 0 — so the bid-time cascade
**never blocks** waiting for the offline pipeline (S3.2) to fill in
a real signature. Downstream consumers can detect cold-miss by
inspecting `confidence_per_dimension` (all zero = neutral fallback).

Latency budget per directive §S6.4 + Enhancement #09:
  Page-priming Feature Store lookup must close in ≤ 5ms p99 within
  the 100ms p99 envelope. L1 hit < 50µs typical; L2 hit ~1-2ms (with
  Redis Cluster RTT); L3 hit ~3-5ms. Cold-miss neutral fallback is
  zero-RTT (in-process construct).

Both L2 and L3 backends are injected by interface (Protocol-style:
expose `get(key) -> Optional[bytes/dict]` + `set(key, value)`)
so this module is testable without live Redis / Memcached.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol, Tuple

from adam.priming.signature import (
    PagePrimingSignature,
    neutral_signature,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Backend protocols (so live Redis/Memcached are injected, not coupled)
# ----------------------------------------------------------------------------

class L2Backend(Protocol):
    """L2 (Redis Cluster) backend interface. Implementations wrap
    redis-py / redis-cluster client; tests use in-memory fakes."""

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    async def set(self, key: str, value: Dict[str, Any]) -> None:
        ...


class L3Backend(Protocol):
    """L3 (Memcached) backend interface. Sync (Memcached client API)
    so the cascade falls through to a synchronous call when L2 misses."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        ...


# ----------------------------------------------------------------------------
# Cascade store
# ----------------------------------------------------------------------------

@dataclass
class CascadeMetrics:
    """Hit-rate + latency metrics per cache tier. Updated in-place;
    snapshot via `snapshot()`."""
    l1_hits: int = 0
    l2_hits: int = 0
    l3_hits: int = 0
    cold_misses: int = 0
    total_lookups: int = 0
    total_latency_us: float = 0.0
    latency_samples_us: list = field(default_factory=list)

    def hit_rate(self, tier: str) -> float:
        if self.total_lookups == 0:
            return 0.0
        attr = getattr(self, f"{tier}_hits", 0)
        return attr / self.total_lookups

    def cold_miss_rate(self) -> float:
        if self.total_lookups == 0:
            return 0.0
        return self.cold_misses / self.total_lookups

    def avg_latency_us(self) -> float:
        if self.total_lookups == 0:
            return 0.0
        return self.total_latency_us / self.total_lookups

    def percentile_latency_us(self, q: float) -> float:
        """q in [0, 100]. Computed from the samples buffer."""
        if not self.latency_samples_us:
            return 0.0
        sorted_samples = sorted(self.latency_samples_us)
        k = max(0, min(len(sorted_samples) - 1,
                       int(round((q / 100.0) * (len(sorted_samples) - 1)))))
        return sorted_samples[k]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "l3_hits": self.l3_hits,
            "cold_misses": self.cold_misses,
            "total_lookups": self.total_lookups,
            "l1_hit_rate": self.hit_rate("l1"),
            "l2_hit_rate": self.hit_rate("l2"),
            "l3_hit_rate": self.hit_rate("l3"),
            "cold_miss_rate": self.cold_miss_rate(),
            "avg_latency_us": self.avg_latency_us(),
            "p50_latency_us": self.percentile_latency_us(50),
            "p99_latency_us": self.percentile_latency_us(99),
            "p99_9_latency_us": self.percentile_latency_us(99.9),
        }


class PagePrimingSignatureStore:
    """L1 LRU + L2 Redis + L3 Memcached cascade with neutral fallback.

    Per directive §S3.3:
      - Lookup key is `url_hash` (SHA-256 hex from pipeline.url_to_hash).
      - Cold-miss returns `neutral_signature(url_hash)` so cascade
        never blocks.
      - Write-through on `put`: writes to L1 + L2 + L3 in parallel.

    L1 is `collections.OrderedDict`-backed LRU with `move_to_end` on
    hit; eviction at `l1_capacity`. L2 + L3 are injected backends.
    """

    def __init__(
        self,
        l1_capacity: int = 1000,
        l2_backend: Optional[L2Backend] = None,
        l3_backend: Optional[L3Backend] = None,
        track_latency: bool = True,
        latency_sample_cap: int = 10_000,
    ) -> None:
        self._l1: "OrderedDict[str, PagePrimingSignature]" = OrderedDict()
        self._l1_capacity = l1_capacity
        self._l2 = l2_backend
        self._l3 = l3_backend
        self._track = track_latency
        self._sample_cap = latency_sample_cap
        self.metrics = CascadeMetrics()

    async def get(self, url_hash: str) -> PagePrimingSignature:
        """Cascade lookup. Returns a signature in all cases — neutral
        on cold miss, real otherwise. Updates metrics (hit/miss + latency).
        """
        t0 = time.perf_counter() if self._track else 0.0
        try:
            # L1
            sig = self._l1.get(url_hash)
            if sig is not None:
                self._l1.move_to_end(url_hash)
                self._record(t0, "l1_hits")
                return sig

            # L2
            if self._l2 is not None:
                row = await self._l2.get(url_hash)
                if row:
                    sig = PagePrimingSignature.from_feature_store_row(row)
                    self._promote_to_l1(sig.url_hash, sig)
                    self._record(t0, "l2_hits")
                    return sig

            # L3 (sync)
            if self._l3 is not None:
                row = self._l3.get(url_hash)
                if row:
                    sig = PagePrimingSignature.from_feature_store_row(row)
                    self._promote_to_l1(sig.url_hash, sig)
                    self._record(t0, "l3_hits")
                    return sig

            # Cold miss → neutral fallback
            sig = neutral_signature(url_hash)
            self._record(t0, "cold_misses")
            return sig
        finally:
            # Increment regardless of which path returned (the named
            # tier increment was done inline)
            self.metrics.total_lookups += 1

    async def put(self, signature: PagePrimingSignature) -> None:
        """Write-through to all available layers."""
        url_hash = signature.url_hash
        self._promote_to_l1(url_hash, signature)
        row = signature.to_feature_store_row()

        coros = []
        if self._l2 is not None:
            coros.append(self._safe_l2_set(url_hash, row))
        if self._l3 is not None:
            try:
                self._l3.set(url_hash, row)
            except Exception as exc:
                logger.warning("L3 set failed for %s: %s", url_hash, exc)

        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def _safe_l2_set(self, key: str, row: Dict[str, Any]) -> None:
        try:
            await self._l2.set(key, row)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("L2 set failed for %s: %s", key, exc)

    async def put_many(
        self, signatures: list,
    ) -> None:
        """Batch write-through. Useful as a `persist_fn` injectable
        into S3.2's `batch_process_urls`."""
        await asyncio.gather(
            *(self.put(s) for s in signatures),
            return_exceptions=True,
        )

    def invalidate(self, url_hash: str) -> bool:
        """Remove from L1 only (L2/L3 carry their own TTLs).
        Returns True if the entry existed in L1."""
        return self._l1.pop(url_hash, None) is not None

    def clear_l1(self) -> int:
        """Drop the entire L1 cache. Returns count of removed entries."""
        n = len(self._l1)
        self._l1.clear()
        return n

    def _promote_to_l1(
        self, url_hash: str, sig: PagePrimingSignature,
    ) -> None:
        if url_hash in self._l1:
            self._l1.move_to_end(url_hash)
            self._l1[url_hash] = sig
        else:
            self._l1[url_hash] = sig
            while len(self._l1) > self._l1_capacity:
                self._l1.popitem(last=False)

    def _record(self, t0: float, hit_type: str) -> None:
        if hit_type == "l1_hits":
            self.metrics.l1_hits += 1
        elif hit_type == "l2_hits":
            self.metrics.l2_hits += 1
        elif hit_type == "l3_hits":
            self.metrics.l3_hits += 1
        elif hit_type == "cold_misses":
            self.metrics.cold_misses += 1
        if self._track:
            elapsed_us = (time.perf_counter() - t0) * 1_000_000
            self.metrics.total_latency_us += elapsed_us
            if len(self.metrics.latency_samples_us) < self._sample_cap:
                self.metrics.latency_samples_us.append(elapsed_us)


# ----------------------------------------------------------------------------
# In-memory backend implementations (for tests + dev-mode)
# ----------------------------------------------------------------------------

class InMemoryL2Backend:
    """In-memory L2 stand-in for tests + dev-mode Feature Store. Async
    interface to match the live Redis client surface; no actual RTT."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    async def set(self, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = value


class InMemoryL3Backend:
    """In-memory L3 stand-in for tests. Sync interface to match
    Memcached client surface."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = value
