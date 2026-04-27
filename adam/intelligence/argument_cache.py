"""Cache layer for audited CLAUDE_ARGUMENT output.

The cascade hot path runs in <120ms (FastAPI /api/v1/stackadapt/creative-
intelligence SLA per handoff §reference-architecture). The CAI generate-
critique-revise loop in M6 runs offline at ~500ms+ per argument — too
slow for the bid path. The architectural pattern from handoff §6.5:

    Offline CAI loop populates the cache → cascade reads from the cache
    sync at request time → cache miss falls through to template path.

Cache key shape:
    informativ:argument:v1:{constitution_version}:{brand_id}:{archetype}:
    {mechanism}:{barrier_hash}

The constitution_version is part of the key so a constitution bump
invalidates everything cached against the prior version. Per handoff §6.8:
'Constitution drift — version constitution; cache key includes
constitution_version; invalidate on bump.'

TTL is 7 days (handoff §6.5). After TTL, the offline populator regenerates
from the freshest brand KB.

This module exposes:
    - get_cached_argument(...)       — sync read on cascade hot path
    - put_cached_argument(...)       — write from offline CAI loop (M6)
    - cache_key(...)                 — stable key derivation (used by both)

It does NOT generate arguments. The CAI loop in M6 is the sole writer.
B3 ships the cache + cascade reader so M6 has a wire to land into.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from adam.intelligence.argument_constitution import CONSTITUTION_VERSION

logger = logging.getLogger(__name__)


_KEY_PREFIX = "informativ:argument:v1"
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days per handoff §6.5


# -----------------------------------------------------------------------------
# Cached argument shape — what the CAI loop produces and the cascade reads
# -----------------------------------------------------------------------------


@dataclass
class CachedArgument:
    """An argument that passed the constitutional rubric.

    Produced by the M6 CAI loop after generate → critique → revise
    converged within max_iter=3 to archetype_fit ≥ 0.85, factscore ≥ 0.95.
    Read sync by the cascade at request time.

    The full headline + body + cta triple is preserved separately so
    the cascade can place each in the StackAdapt response shape without
    re-parsing concatenated text.
    """

    headline: str = ""
    body: str = ""
    cta: str = ""
    barrier_addressed: str = ""
    archetype_fit_score: float = 0.0
    factscore: float = 0.0
    iterations_to_converge: int = 0
    constitution_version: str = CONSTITUTION_VERSION
    # Track which mechanism the rubric audited against — round-trip
    # discipline so the cascade's resolved primary_mechanism can be
    # asserted against the cached argument's mechanism at read time.
    mechanism_audited: str = ""
    archetype_audited: str = ""
    # Free-form provenance — model name, generation timestamp, KB version
    provenance: dict = field(default_factory=dict)


def _serialize(arg: CachedArgument) -> str:
    return json.dumps(asdict(arg), default=str)


def _deserialize(payload: str) -> Optional[CachedArgument]:
    try:
        d = json.loads(payload)
    except (TypeError, ValueError):
        return None
    try:
        return CachedArgument(**d)
    except TypeError as exc:
        # Schema drift — payload was written under a different shape.
        # Treat as cache miss; the offline populator will rewrite.
        logger.debug("Cached argument deserialization failed (%s); treating as miss", exc)
        return None


# -----------------------------------------------------------------------------
# Key derivation — stable across processes and Python versions
# -----------------------------------------------------------------------------


def barrier_hash(barrier: str) -> str:
    """Stable short hash of the barrier string.

    The handoff §6.5 cache key includes a barrier_hash so the same
    (brand, archetype, mechanism) triple can carry distinct arguments
    for distinct diagnosed barriers (trust_deficit vs price_objection
    vs competitive_alternative_anchored). 8 hex chars = 32 bits = vanishing
    collision risk within a single brand's barrier vocabulary (~10s of
    barriers).
    """
    return hashlib.sha256((barrier or "").encode("utf-8")).hexdigest()[:8]


def cache_key(
    brand_id: str,
    archetype: str,
    mechanism: str,
    barrier: str,
    constitution_version: str = CONSTITUTION_VERSION,
) -> str:
    """Derive the canonical cache key for a (brand, archetype, mechanism,
    barrier) cell under the current constitution version.

    Lower-cased archetype and mechanism so cascade-side casing variations
    don't fragment the cache. Brand id is preserved as-is — brand
    namespaces are case-meaningful in StackAdapt's surface.
    """
    bh = barrier_hash(barrier)
    return (
        f"{_KEY_PREFIX}:{constitution_version}:{brand_id}"
        f":{archetype.lower()}:{mechanism.lower()}:{bh}"
    )


# -----------------------------------------------------------------------------
# Hot-path read — cascade calls this; must be sync, must soft-fail
# -----------------------------------------------------------------------------


def get_cached_argument(
    brand_id: str,
    archetype: str,
    mechanism: str,
    barrier: str,
) -> Optional[CachedArgument]:
    """Read an audited argument from cache. Returns None on miss.

    Guarantees:
      - Sync (cascade hot path is sync end-to-end).
      - Never raises. Redis unreachable → None. Deserialization failure
        → None. Schema drift → None.
      - Mechanism + archetype round-trip check: if the cached argument
        was audited against a DIFFERENT mechanism than the cascade's
        resolved one, return None — we will not let a mechanism-faithful
        rubric on argument A apply to a cascade decision for mechanism B.
    """
    try:
        from adam.infrastructure.redis_client import get_redis
        client = get_redis()
    except Exception as exc:
        logger.debug("Argument cache read: redis client import failed (%s)", exc)
        return None
    if client is None:
        return None

    key = cache_key(brand_id, archetype, mechanism, barrier)
    try:
        payload = client.get(key)
    except Exception as exc:
        logger.debug("Argument cache read failed for %s (%s)", key, exc)
        return None
    if payload is None:
        return None

    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    arg = _deserialize(payload)
    if arg is None:
        return None

    # Round-trip discipline — mechanism_faithful is the architectural
    # commitment that the rubric on this argument matches the cascade's
    # current decision. Mismatch returns miss rather than serving the
    # wrong-mechanism creative.
    if arg.mechanism_audited and arg.mechanism_audited.lower() != mechanism.lower():
        logger.warning(
            "Argument cache mechanism mismatch: cached=%s requested=%s key=%s",
            arg.mechanism_audited, mechanism, key,
        )
        return None
    if arg.archetype_audited and arg.archetype_audited.lower() != archetype.lower():
        logger.warning(
            "Argument cache archetype mismatch: cached=%s requested=%s key=%s",
            arg.archetype_audited, archetype, key,
        )
        return None

    return arg


# -----------------------------------------------------------------------------
# Offline write — M6 CAI loop will call this; out-of-band of the cascade
# -----------------------------------------------------------------------------


def put_cached_argument(
    brand_id: str,
    archetype: str,
    mechanism: str,
    barrier: str,
    argument: CachedArgument,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Write an audited argument to cache. Returns True on success.

    Stamps mechanism_audited / archetype_audited / constitution_version
    onto the argument before write so the read-side round-trip check
    can detect drift. Soft-fails when Redis is unreachable.

    Caller's responsibility: only call this with arguments that PASSED
    the constitutional rubric. The cache trusts upstream gating; it is
    not a second checkpoint.
    """
    try:
        from adam.infrastructure.redis_client import get_redis
        client = get_redis()
    except Exception as exc:
        logger.debug("Argument cache write: redis client import failed (%s)", exc)
        return False
    if client is None:
        return False

    # Stamp the round-trip metadata onto the argument so reader-side
    # mismatch checks have something to compare against.
    argument.mechanism_audited = mechanism
    argument.archetype_audited = archetype
    argument.constitution_version = CONSTITUTION_VERSION

    key = cache_key(brand_id, archetype, mechanism, barrier)
    try:
        client.set(key, _serialize(argument), ex=ttl_seconds)
        return True
    except Exception as exc:
        logger.warning("Argument cache write failed for %s (%s)", key, exc)
        return False


def invalidate_cached_argument(
    brand_id: str,
    archetype: str,
    mechanism: str,
    barrier: str,
) -> bool:
    """Delete a cached argument. Returns True if a key was removed.

    Use case: the offline regeneration job has produced a replacement
    argument and wants to force-evict before TTL.
    """
    try:
        from adam.infrastructure.redis_client import get_redis
        client = get_redis()
    except Exception:
        return False
    if client is None:
        return False
    key = cache_key(brand_id, archetype, mechanism, barrier)
    try:
        return bool(client.delete(key))
    except Exception:
        return False


def assemble_primary_text(arg: CachedArgument) -> str:
    """Concatenate headline + body + cta into the single primary_text
    shape that downstream creative consumers expect (matches the legacy
    template path's shape in copy_generation.service)."""
    parts: List[str] = []
    if arg.headline:
        parts.append(arg.headline.strip())
    if arg.body:
        parts.append(arg.body.strip())
    if arg.cta:
        parts.append(arg.cta.strip())
    return " ".join(parts)
