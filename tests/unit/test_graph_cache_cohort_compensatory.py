"""F.2 / S6.1 (2 of 2) — get_cohort_compensatory_flag bid-time
sibling accessor on GraphIntelligenceCache.

Q14.B=(β) sibling-accessor design: the new method is deliberately
SEPARATE from get_cohort_priors (which returns Dict[str, float] of
mechanism effectiveness) to avoid type-confusing per-mechanism
scalars with a cohort-level boolean flag.

These tests use minimal mocks against the cache to avoid spinning
up Neo4j. The cypher path is exercised at the boundary; the
returned-record handling and backward-compat behavior are pinned.
"""
import threading
import time
from unittest.mock import MagicMock

import pytest

from adam.api.stackadapt.graph_cache import GraphIntelligenceCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bare_cache() -> GraphIntelligenceCache:
    """Construct a GraphIntelligenceCache without invoking __init__'s
    Neo4j-touching setup. We only need the lock + caches + accessor
    method on the instance."""
    cache = GraphIntelligenceCache.__new__(GraphIntelligenceCache)
    cache._lock = threading.Lock()
    cache._cohort_priors = {}
    cache._cohort_compensatory_flags = {}
    return cache


def _mock_driver_returning(record_dict):
    """Build a mock Neo4j driver whose session.run().single() returns
    a record-like object with the provided field mapping."""
    driver = MagicMock()
    record_obj = MagicMock()
    record_obj.get = lambda key, default=None: record_dict.get(key, default)
    session = MagicMock()
    session.run.return_value.single.return_value = record_dict and record_obj
    driver.session.return_value.__enter__ = lambda *_: session
    driver.session.return_value.__exit__ = lambda *_: None
    return driver


# ---------------------------------------------------------------------------
# Default-return paths (no driver / empty buyer / pre-F.2 cohorts)
# ---------------------------------------------------------------------------

class TestDefaultReturnPaths:

    def test_empty_buyer_id_returns_neutral_default(self):
        """Test 13a: empty buyer_id → (False, 0.50) without query."""
        cache = _bare_cache()
        assert cache.get_cohort_compensatory_flag("") == (False, 0.50)

    def test_no_driver_returns_neutral_default(self):
        """Test 13b: no Neo4j driver → (False, 0.50)."""
        cache = _bare_cache()
        cache._get_driver = lambda: None
        assert cache.get_cohort_compensatory_flag("u1") == (False, 0.50)

    def test_pre_f2_cohort_with_none_fields_returns_neutral(self):
        """Test 14: backward-compat with pre-F.2 persisted cohorts.
        Cohort node lacks the F.2 properties → record returns None
        for both fields → accessor returns (False, 0.50)."""
        cache = _bare_cache()
        cache._get_driver = lambda: _mock_driver_returning(
            {"flag": None, "confidence": None},
        )
        assert cache.get_cohort_compensatory_flag("u_pre_f2") == (
            False, 0.50,
        )


# ---------------------------------------------------------------------------
# Populated-flag path
# ---------------------------------------------------------------------------

class TestPopulatedFlagPath:

    def test_returns_flag_and_confidence_for_known_buyer(self):
        """Test 12: known buyer with F.2-populated cohort →
        (True, 0.85)."""
        cache = _bare_cache()
        cache._get_driver = lambda: _mock_driver_returning(
            {"flag": True, "confidence": 0.85},
        )
        assert cache.get_cohort_compensatory_flag("u_known") == (
            True, 0.85,
        )

    def test_returns_false_with_partial_evidence_confidence(self):
        """A cohort with criterion_2-only evidence → (False, 0.65)."""
        cache = _bare_cache()
        cache._get_driver = lambda: _mock_driver_returning(
            {"flag": False, "confidence": 0.65},
        )
        assert cache.get_cohort_compensatory_flag("u_partial") == (
            False, 0.65,
        )


# ---------------------------------------------------------------------------
# Caching behavior
# ---------------------------------------------------------------------------

class TestCachingBehavior:

    def test_second_lookup_reads_from_cache_not_driver(self):
        """After a successful lookup, a second call within TTL should
        not invoke the driver again."""
        cache = _bare_cache()
        # Manually pre-populate the cache to confirm cache-hit path.
        cache._cohort_compensatory_flags["u_cached"] = (
            True, 0.85, time.time(),
        )
        # Set a driver that would explode if invoked — proves we
        # never reach it.
        cache._get_driver = lambda: (_ for _ in ()).throw(
            RuntimeError("driver should NOT be touched on cache hit"),
        )
        assert cache.get_cohort_compensatory_flag("u_cached") == (
            True, 0.85,
        )

    def test_expired_cache_entry_re_queries(self):
        """Cache entry past TTL should fall through to driver."""
        cache = _bare_cache()
        # Pre-populate with a stale entry (TTL is 30 minutes; set ts 1
        # hour ago).
        stale_ts = time.time() - 3600
        cache._cohort_compensatory_flags["u_stale"] = (
            False, 0.50, stale_ts,
        )
        cache._get_driver = lambda: _mock_driver_returning(
            {"flag": True, "confidence": 0.85},
        )
        # New lookup should reach the driver and update the cache.
        assert cache.get_cohort_compensatory_flag("u_stale") == (
            True, 0.85,
        )


# ---------------------------------------------------------------------------
# Latency budget
# ---------------------------------------------------------------------------

class TestLatencyBudget:

    def test_cached_accessor_p99_under_1ms(self):
        """Test 15: with cache populated, p99 latency for 10,000 calls
        is well under 1ms. Cached path is dict lookup only."""
        cache = _bare_cache()
        cache._cohort_compensatory_flags["u_lat"] = (
            True, 0.85, time.time(),
        )
        cache._get_driver = lambda: None  # driver shouldn't be reached

        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            cache.get_cohort_compensatory_flag("u_lat")
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 1000, (
            f"p99 latency {p99:.1f}μs exceeds 1ms bid-time budget"
        )


# ---------------------------------------------------------------------------
# Cache coherence with get_cohort_priors
# ---------------------------------------------------------------------------

class TestCacheCoherence:

    def test_compensatory_flag_and_priors_are_independent_caches(self):
        """Test 16: get_cohort_priors and get_cohort_compensatory_flag
        cache to separate per-buyer dicts (priors / flag have different
        types). Pin that the two caches don't interfere with each other.

        This is also the structural pin for Q14.B=(β): sibling accessor,
        separate cache, separate semantic — NOT extending the priors
        return type or encoding flags inside the priors blob.
        """
        cache = _bare_cache()
        # Pre-populate compensatory cache.
        cache._cohort_compensatory_flags["u_coh"] = (
            True, 0.85, time.time(),
        )
        # Pre-populate priors cache with mechanism scores (different
        # type — Dict[str, float]).
        cache._cohort_priors["u_coh"] = (
            {"social_proof": 0.72, "liking": 0.65}, time.time(),
        )
        # Both caches should remain independently readable.
        assert "u_coh" in cache._cohort_compensatory_flags
        assert "u_coh" in cache._cohort_priors
        flag, conf = cache.get_cohort_compensatory_flag("u_coh")
        assert (flag, conf) == (True, 0.85)


# ---------------------------------------------------------------------------
# Zero-regression on existing get_cohort_priors
# ---------------------------------------------------------------------------

class TestZeroRegression:

    def test_get_cohort_priors_signature_unchanged(self):
        """Test 18: F.2 only ADDS a sibling accessor; the existing
        get_cohort_priors signature and return type are unchanged."""
        import inspect
        sig = inspect.signature(GraphIntelligenceCache.get_cohort_priors)
        params = list(sig.parameters)
        # (self, buyer_id) — exactly 2 params.
        assert params == ["self", "buyer_id"]
        # Return annotation should still be Dict[str, float].
        return_ann = sig.return_annotation
        assert "Dict" in str(return_ann) or "dict" in str(return_ann), (
            f"get_cohort_priors return annotation changed: {return_ann}"
        )

    def test_compensatory_accessor_method_present(self):
        """Sanity: the new method is an attribute of the class."""
        assert hasattr(
            GraphIntelligenceCache, "get_cohort_compensatory_flag",
        )
