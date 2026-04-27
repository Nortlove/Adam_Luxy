"""Pin the metaphor bundle storage layer + cascade-side F3 wire.

Discipline anchors:
    - Sync read on cascade hot path; soft-fail to None on every error
      path (Redis unreachable, malformed JSON, schema drift, missing
      identifier). Bid path must NEVER block on metaphor storage.
    - Schema-version key ('v1') in the cache key. A future bundle-
      shape change bumps the version; old keys naturally expire via
      TTL rather than needing migration.
    - Cascade wire: when EITHER bundle missing or low-confidence,
      edge_dimensions stays without 'metaphor_alignment' key —
      honest 'no signal' rather than fabricating a value.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.brand_copy_metaphor_scoring import BrandCopyMetaphorBundle
from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.metaphor_storage import (
    get_brand_metaphor_bundle,
    get_buyer_metaphor_bundle,
    put_brand_metaphor_bundle,
    put_buyer_metaphor_bundle,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


# =============================================================================
# Buyer storage — read path soft-fails
# =============================================================================


def test_buyer_get_returns_none_on_empty_id():
    """Empty buyer_id → None without touching Redis."""
    redis_mock = MagicMock()
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("")
    assert result is None
    redis_mock.get.assert_not_called()


def test_buyer_get_returns_none_when_redis_unavailable():
    with patch("adam.infrastructure.redis_client.get_redis", return_value=None):
        result = get_buyer_metaphor_bundle("b1")
    assert result is None


def test_buyer_get_returns_none_on_cache_miss():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is None


def test_buyer_get_returns_bundle_on_hit():
    bundle = BuyerMetaphorBundle(
        primary_metaphor_axes=[0.5] * _NUM_AXES,
        metaphor_density=0.6, confidence=0.75,
        buyer_id="b1",
    )
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "primary_metaphor_axes": list(bundle.primary_metaphor_axes),
        "metaphor_density": bundle.metaphor_density,
        "confidence": bundle.confidence,
        "review_id": "",
        "buyer_id": "b1",
    }))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is not None
    assert result.confidence == 0.75
    assert result.metaphor_density == 0.6
    assert result.buyer_id == "b1"


def test_buyer_get_handles_malformed_json():
    """Garbage payload → None, no exception."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value="not json {{{ ")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is None


def test_buyer_get_handles_schema_drift():
    """JSON that's missing required fields or has unknown fields →
    None. Offline F1 runner overwrites on next pass."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "totally_different_shape": True,
    }))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is None


def test_buyer_get_handles_redis_exception():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(side_effect=ConnectionError("net"))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is None


def test_buyer_get_handles_bytes_payload():
    """Some Redis clients return bytes; decode to string first."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "primary_metaphor_axes": [0.0] * _NUM_AXES,
        "metaphor_density": 0.0, "confidence": 0.0,
        "review_id": "", "buyer_id": "b1",
    }).encode("utf-8"))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_buyer_metaphor_bundle("b1")
    assert result is not None


# =============================================================================
# Buyer storage — write path
# =============================================================================


def test_buyer_put_writes_under_canonical_key():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    bundle = BuyerMetaphorBundle(
        primary_metaphor_axes=[0.0] * _NUM_AXES,
        metaphor_density=0.5, confidence=0.7,
        buyer_id="b42",
    )
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_buyer_metaphor_bundle(bundle)
    assert ok is True
    key = redis_mock.set.call_args.args[0]
    assert key == "informativ:metaphor:buyer:v1:b42"


def test_buyer_put_writes_30_day_ttl():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    bundle = BuyerMetaphorBundle(buyer_id="b1", confidence=0.5)
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_buyer_metaphor_bundle(bundle)
    kwargs = redis_mock.set.call_args.kwargs
    assert kwargs.get("ex") == 30 * 24 * 3600


def test_buyer_put_returns_false_on_empty_id():
    bundle = BuyerMetaphorBundle(buyer_id="", confidence=0.5)
    redis_mock = MagicMock()
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_buyer_metaphor_bundle(bundle)
    assert ok is False


def test_buyer_put_returns_false_when_redis_unavailable():
    bundle = BuyerMetaphorBundle(buyer_id="b1")
    with patch("adam.infrastructure.redis_client.get_redis", return_value=None):
        ok = put_buyer_metaphor_bundle(bundle)
    assert ok is False


# =============================================================================
# Brand storage — same patterns as buyer storage
# =============================================================================


def test_brand_get_returns_none_on_empty_asin():
    redis_mock = MagicMock()
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_brand_metaphor_bundle("")
    assert result is None


def test_brand_get_returns_bundle_on_hit():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=json.dumps({
        "primary_metaphor_axes": [0.5] * _NUM_AXES,
        "metaphor_density": 0.4, "confidence": 0.8,
        "asin": "lux_luxy_ride", "brand_id": "luxy",
    }))
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        result = get_brand_metaphor_bundle("lux_luxy_ride")
    assert result is not None
    assert result.asin == "lux_luxy_ride"
    assert result.confidence == 0.8


def test_brand_put_writes_under_canonical_key():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    bundle = BrandCopyMetaphorBundle(
        primary_metaphor_axes=[0.0] * _NUM_AXES,
        metaphor_density=0.3, confidence=0.6,
        asin="lux_luxy_ride", brand_id="luxy",
    )
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_brand_metaphor_bundle(bundle)
    assert ok is True
    key = redis_mock.set.call_args.args[0]
    assert key == "informativ:metaphor:brand:v1:lux_luxy_ride"


def test_brand_put_returns_false_on_empty_asin():
    bundle = BrandCopyMetaphorBundle(asin="", confidence=0.5)
    redis_mock = MagicMock()
    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        ok = put_brand_metaphor_bundle(bundle)
    assert ok is False


# =============================================================================
# Round-trip: write then read
# =============================================================================


def test_buyer_round_trip_write_then_read():
    storage = {}
    redis_mock = MagicMock()
    redis_mock.set = MagicMock(side_effect=lambda k, v, ex=None: storage.update({k: v}))
    redis_mock.get = MagicMock(side_effect=lambda k: storage.get(k))

    original = BuyerMetaphorBundle(
        primary_metaphor_axes=[0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        metaphor_density=0.55,
        confidence=0.8,
        review_id="r1",
        buyer_id="b1",
    )

    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_buyer_metaphor_bundle(original)
        retrieved = get_buyer_metaphor_bundle("b1")

    assert retrieved is not None
    assert retrieved.metaphor_density == 0.55
    assert retrieved.confidence == 0.8
    assert retrieved.primary_metaphor_axes[0] == 0.7
    assert retrieved.buyer_id == "b1"


def test_brand_round_trip_write_then_read():
    storage = {}
    redis_mock = MagicMock()
    redis_mock.set = MagicMock(side_effect=lambda k, v, ex=None: storage.update({k: v}))
    redis_mock.get = MagicMock(side_effect=lambda k: storage.get(k))

    original = BrandCopyMetaphorBundle(
        primary_metaphor_axes=[0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0],
        metaphor_density=0.5,
        confidence=0.7,
        asin="lux_luxy_ride",
        brand_id="luxy",
    )

    with patch("adam.infrastructure.redis_client.get_redis", return_value=redis_mock):
        put_brand_metaphor_bundle(original)
        retrieved = get_brand_metaphor_bundle("lux_luxy_ride")

    assert retrieved is not None
    assert retrieved.asin == "lux_luxy_ride"
    assert retrieved.primary_metaphor_axes[0] == 0.6
    assert retrieved.primary_metaphor_axes[6] == 0.5
