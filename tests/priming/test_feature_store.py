"""S3.3 — page-priming Feature Store cascade tests.

Per directive §S3.3 closure: cascade L1 → L2 → L3 → cold-miss
neutral fallback; p99 lookup latency on a 10k-URL synthetic load
< 5ms with realistic L1 hit rates. Tests pin:
  - L1 hit / L1 miss → L2 hit (with promotion) / L2 miss → L3 hit /
    all miss → neutral fallback
  - Write-through to all available backends
  - LRU eviction at capacity
  - Cold-miss neutral floors confidence_per_dimension at 0
  - Synthetic 10k load latency target
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import pytest

from adam.priming import PagePrimingSignature, neutral_signature
from adam.priming.feature_store import (
    CascadeMetrics,
    InMemoryL2Backend,
    InMemoryL3Backend,
    PagePrimingSignatureStore,
)


def _sig(url_hash="hash_x", valence=0.5, arousal=0.7):
    return PagePrimingSignature(
        url_hash=url_hash,
        valence=valence, arousal=arousal,
        regulatory_focus_priming="promotion",
        cognitive_load_estimate=0.3,
        activated_frames=("social_proof",),
        confidence_per_dimension={
            "valence": 0.9, "arousal": 0.9,
            "regulatory_focus_priming": 0.9,
            "cognitive_load_estimate": 0.9,
            "activated_frames": 0.9,
        },
    )


# ----------------------------------------------------------------------------
# Cascade tier hits
# ----------------------------------------------------------------------------

class TestL1Hit:
    @pytest.mark.asyncio
    async def test_l1_hit_after_put(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        sig = _sig("h1")
        await store.put(sig)
        result = await store.get("h1")
        assert result == sig
        assert store.metrics.l1_hits == 1
        assert store.metrics.cold_misses == 0


class TestL2Hit:
    @pytest.mark.asyncio
    async def test_l1_miss_l2_hit_promotes_to_l1(self):
        l2 = InMemoryL2Backend()
        store = PagePrimingSignatureStore(l1_capacity=10, l2_backend=l2)
        sig = _sig("h2")
        # Put goes to BOTH L1 + L2 (write-through). To test L2 hit we
        # need to invalidate L1 first.
        await store.put(sig)
        store.invalidate("h2")
        # Now L1 misses, L2 hits.
        result = await store.get("h2")
        assert result == sig
        assert store.metrics.l1_hits == 0
        assert store.metrics.l2_hits == 1
        # L2 hit should promote into L1.
        assert "h2" in store._l1


class TestL3Hit:
    @pytest.mark.asyncio
    async def test_l1_miss_l2_miss_l3_hit_promotes_to_l1(self):
        l2 = InMemoryL2Backend()
        l3 = InMemoryL3Backend()
        store = PagePrimingSignatureStore(
            l1_capacity=10, l2_backend=l2, l3_backend=l3,
        )
        sig = _sig("h3")
        await store.put(sig)
        # Invalidate L1 + L2 to force L3-only hit
        store.invalidate("h3")
        l2._store.clear()
        result = await store.get("h3")
        assert result == sig
        assert store.metrics.l3_hits == 1
        assert "h3" in store._l1  # promoted


class TestColdMissNeutralFallback:
    @pytest.mark.asyncio
    async def test_all_miss_returns_neutral(self):
        store = PagePrimingSignatureStore()
        result = await store.get("never_seen")
        # Cold miss → neutral signature with all-zero confidence
        assert result.url_hash == "never_seen"
        assert result.valence == 0.0
        assert result.arousal == 0.0
        assert result.regulatory_focus_priming == "neutral"
        assert all(v == 0.0
                   for v in result.confidence_per_dimension.values())
        assert store.metrics.cold_misses == 1

    @pytest.mark.asyncio
    async def test_cold_miss_does_not_block(self):
        # No L2/L3 backends configured; cold-miss must still resolve
        # synchronously without raising.
        store = PagePrimingSignatureStore()
        result = await asyncio.wait_for(store.get("x"), timeout=1.0)
        assert result is not None

    @pytest.mark.asyncio
    async def test_consumer_can_detect_cold_miss(self):
        """Per directive §S3.3: cold-miss confidence floored at 0
        across all dims so downstream consumers detect the case."""
        store = PagePrimingSignatureStore()
        sig = await store.get("missed")
        # Detection rule: all confidences zero ⇔ neutral fallback
        is_cold_miss = all(
            v == 0.0 for v in sig.confidence_per_dimension.values()
        )
        assert is_cold_miss


# ----------------------------------------------------------------------------
# Write-through
# ----------------------------------------------------------------------------

class TestWriteThrough:
    @pytest.mark.asyncio
    async def test_put_writes_to_all_layers(self):
        l2 = InMemoryL2Backend()
        l3 = InMemoryL3Backend()
        store = PagePrimingSignatureStore(
            l1_capacity=10, l2_backend=l2, l3_backend=l3,
        )
        sig = _sig("w1")
        await store.put(sig)
        assert "w1" in store._l1
        assert "w1" in l2._store
        assert "w1" in l3._store

    @pytest.mark.asyncio
    async def test_put_with_no_l2_l3_writes_l1_only(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        sig = _sig("w2")
        await store.put(sig)
        assert "w2" in store._l1

    @pytest.mark.asyncio
    async def test_put_many_batch(self):
        l2 = InMemoryL2Backend()
        store = PagePrimingSignatureStore(l1_capacity=100, l2_backend=l2)
        sigs = [_sig(f"h{i}") for i in range(10)]
        await store.put_many(sigs)
        for i in range(10):
            assert f"h{i}" in store._l1
            assert f"h{i}" in l2._store

    @pytest.mark.asyncio
    async def test_l2_set_failure_does_not_block_l1_write(self):
        class FailingL2:
            async def get(self, key): return None
            async def set(self, key, value):
                raise ConnectionError("Redis down")
        store = PagePrimingSignatureStore(
            l1_capacity=10, l2_backend=FailingL2(),
        )
        sig = _sig("w3")
        await store.put(sig)  # should not raise
        assert "w3" in store._l1


# ----------------------------------------------------------------------------
# LRU eviction
# ----------------------------------------------------------------------------

class TestLRUEviction:
    @pytest.mark.asyncio
    async def test_eviction_at_capacity(self):
        store = PagePrimingSignatureStore(l1_capacity=3)
        # Fill to capacity
        for i in range(3):
            await store.put(_sig(f"h{i}"))
        assert len(store._l1) == 3
        # Add one more → oldest evicted
        await store.put(_sig("h_new"))
        assert len(store._l1) == 3
        assert "h_new" in store._l1
        assert "h0" not in store._l1  # h0 was oldest, evicted

    @pytest.mark.asyncio
    async def test_get_promotes_lru_order(self):
        store = PagePrimingSignatureStore(l1_capacity=3)
        for i in range(3):
            await store.put(_sig(f"h{i}"))
        # Access h0 (the oldest) → moves to end (most recent)
        await store.get("h0")
        # Now adding h_new evicts h1 (the new oldest), not h0
        await store.put(_sig("h_new"))
        assert "h0" in store._l1
        assert "h1" not in store._l1
        assert "h_new" in store._l1

    @pytest.mark.asyncio
    async def test_repeated_put_does_not_overflow(self):
        store = PagePrimingSignatureStore(l1_capacity=5)
        for i in range(20):
            await store.put(_sig(f"h{i}"))
        assert len(store._l1) == 5
        # Last 5 should be present
        for i in range(15, 20):
            assert f"h{i}" in store._l1


# ----------------------------------------------------------------------------
# Metrics + percentile latency
# ----------------------------------------------------------------------------

class TestMetrics:
    @pytest.mark.asyncio
    async def test_hit_rate_computation(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        await store.put(_sig("h1"))
        await store.get("h1")  # L1 hit
        await store.get("h2")  # cold miss
        snap = store.metrics.snapshot()
        assert snap["l1_hits"] == 1
        assert snap["cold_misses"] == 1
        assert snap["total_lookups"] == 2
        assert snap["l1_hit_rate"] == 0.5
        assert snap["cold_miss_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_latency_samples_collected(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        for i in range(50):
            await store.put(_sig(f"h{i}"))
        for i in range(50):
            await store.get(f"h{i}")
        snap = store.metrics.snapshot()
        assert snap["total_lookups"] == 50
        assert snap["avg_latency_us"] >= 0
        assert snap["p99_latency_us"] >= 0


# ----------------------------------------------------------------------------
# Synthetic 10k load — p99 < 5ms target
# ----------------------------------------------------------------------------

class TestSyntheticLoadLatency:
    @pytest.mark.asyncio
    async def test_10k_lookups_p99_under_5ms_l1_only(self):
        """Per directive §S3.3 closure criterion: p99 < 5ms on a
        10k-URL synthetic load. With L1-only (in-process), this is a
        floor-test — real production includes L2/L3 RTTs that would
        push p99 toward 5ms; in-process p99 should be well under."""
        store = PagePrimingSignatureStore(l1_capacity=10_000)
        # Pre-populate L1 with 8k signatures so 80% of the 10k
        # lookups hit L1 (realistic L1 hit-rate).
        for i in range(8_000):
            await store.put(_sig(f"h{i}"))
        # Reset metrics to ignore the put latencies
        store.metrics = CascadeMetrics()

        # Issue 10k lookups: 80% hit (h0..h7999), 20% cold miss.
        for i in range(10_000):
            key = f"h{i if i < 8000 else 'cold_' + str(i)}"
            await store.get(key)

        snap = store.metrics.snapshot()
        assert snap["total_lookups"] == 10_000
        # In-process L1 + cold-miss-neutral should be well under 5ms p99.
        # Set a generous 5000us = 5ms ceiling per directive.
        assert snap["p99_latency_us"] < 5000.0, (
            f"p99 {snap['p99_latency_us']:.1f}us exceeds 5ms target"
        )
        # L1 hit rate near 80%
        assert 0.75 <= snap["l1_hit_rate"] <= 0.85
        assert 0.15 <= snap["cold_miss_rate"] <= 0.25


# ----------------------------------------------------------------------------
# invalidate + clear
# ----------------------------------------------------------------------------

class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_removes_from_l1(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        await store.put(_sig("h1"))
        assert store.invalidate("h1") is True
        assert "h1" not in store._l1

    @pytest.mark.asyncio
    async def test_invalidate_returns_false_for_missing(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        assert store.invalidate("never_existed") is False

    @pytest.mark.asyncio
    async def test_clear_l1(self):
        store = PagePrimingSignatureStore(l1_capacity=10)
        for i in range(5):
            await store.put(_sig(f"h{i}"))
        n = store.clear_l1()
        assert n == 5
        assert len(store._l1) == 0
