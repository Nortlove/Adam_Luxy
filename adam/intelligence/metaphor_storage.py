"""Redis-backed storage for F1 (buyer) and F2 (brand) metaphor bundles.

The cascade hot path needs to read both bundles in <2ms to compute F3's
bilateral metaphor_alignment dimension. Mirrors B3's argument_cache
pattern: sync Redis read with soft-fail to None.

Storage shape:
    informativ:metaphor:buyer:v1:{buyer_id}    → BuyerMetaphorBundle JSON
    informativ:metaphor:brand:v1:{asin}        → BrandCopyMetaphorBundle JSON

TTL: 30 days (buyer profiles are slow-moving traits; brand copy can
update on rebrand). Cache-miss is the honest 'no signal yet' state —
F3 alignment returns neutral when either bundle is missing, so cascade
edge_dimensions["metaphor_alignment"] simply stays absent.

Discipline:
    - Sync read; never raises; soft-fail to None on every error
      (Redis unreachable, malformed payload, schema drift).
    - Write API exists for the offline F1 / F2 scoring runners; the
      cascade only READS.
    - Schema-version key (v1) lets a future bundle-shape change
      invalidate cleanly via a version bump rather than a migration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Optional

from adam.intelligence.brand_copy_metaphor_scoring import BrandCopyMetaphorBundle
from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle

logger = logging.getLogger(__name__)


_BUYER_KEY_PREFIX = "informativ:metaphor:buyer:v1"
_BRAND_KEY_PREFIX = "informativ:metaphor:brand:v1"
_DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 days


# -----------------------------------------------------------------------------
# Buyer metaphor bundle — sync read on cascade hot path
# -----------------------------------------------------------------------------


def get_buyer_metaphor_bundle(
    buyer_id: str,
    redis_client: Optional[Any] = None,
) -> Optional[BuyerMetaphorBundle]:
    """Read a buyer's metaphor bundle from Redis. None on miss / error.

    Cascade hot-path read. Must be sync, must never raise. The cascade
    reads this once per decision and falls through to neutral
    metaphor_alignment when None is returned.
    """
    if not buyer_id:
        return None
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return None
    if redis_client is None:
        return None

    key = f"{_BUYER_KEY_PREFIX}:{buyer_id}"
    try:
        payload = redis_client.get(key)
    except Exception as exc:
        logger.debug("Buyer metaphor read failed for %s: %s", buyer_id, exc)
        return None
    if payload is None:
        return None

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        d = json.loads(payload)
    except (TypeError, ValueError):
        return None

    try:
        return BuyerMetaphorBundle(**d)
    except TypeError as exc:
        # Schema drift (extra/missing fields) — treat as miss; offline
        # F1 runner will overwrite next time it processes this buyer.
        logger.debug(
            "Buyer metaphor schema drift for %s: %s", buyer_id, exc,
        )
        return None


def put_buyer_metaphor_bundle(
    bundle: BuyerMetaphorBundle,
    redis_client: Optional[Any] = None,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Write a buyer's metaphor bundle. Called by the offline F1 runner.

    Returns True on success, False on Redis unavailable / write error.
    """
    if not bundle.buyer_id:
        return False
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return False
    if redis_client is None:
        return False

    key = f"{_BUYER_KEY_PREFIX}:{bundle.buyer_id}"
    try:
        redis_client.set(key, json.dumps(asdict(bundle)), ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning(
            "Buyer metaphor write failed for %s: %s", bundle.buyer_id, exc,
        )
        return False


# -----------------------------------------------------------------------------
# Brand copy metaphor bundle — sync read on cascade hot path
# -----------------------------------------------------------------------------


def get_brand_metaphor_bundle(
    asin: str,
    redis_client: Optional[Any] = None,
) -> Optional[BrandCopyMetaphorBundle]:
    """Read a brand's metaphor bundle from Redis. None on miss / error."""
    if not asin:
        return None
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return None
    if redis_client is None:
        return None

    key = f"{_BRAND_KEY_PREFIX}:{asin}"
    try:
        payload = redis_client.get(key)
    except Exception as exc:
        logger.debug("Brand metaphor read failed for %s: %s", asin, exc)
        return None
    if payload is None:
        return None

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        d = json.loads(payload)
    except (TypeError, ValueError):
        return None

    try:
        return BrandCopyMetaphorBundle(**d)
    except TypeError as exc:
        logger.debug("Brand metaphor schema drift for %s: %s", asin, exc)
        return None


def put_brand_metaphor_bundle(
    bundle: BrandCopyMetaphorBundle,
    redis_client: Optional[Any] = None,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Write a brand's metaphor bundle. Called by offline F2 runner."""
    if not bundle.asin:
        return False
    if redis_client is None:
        try:
            from adam.infrastructure.redis_client import get_redis
            redis_client = get_redis()
        except Exception:
            return False
    if redis_client is None:
        return False

    key = f"{_BRAND_KEY_PREFIX}:{bundle.asin}"
    try:
        redis_client.set(key, json.dumps(asdict(bundle)), ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning(
            "Brand metaphor write failed for %s: %s", bundle.asin, exc,
        )
        return False
