"""Synchronous Redis client for daily-task code paths.

The async-side Redis client (`adam/infrastructure/redis/cache.py` →
`ADAMRedisCache`) is consumed from FastAPI handlers and orchestrator
async paths. The DCIL daily-strengthening tasks (task_23 through task_32),
the dcil_bridge service, and a handful of other ingestion utilities
were written against a synchronous Redis API and import
`from adam.infrastructure.redis_client import get_redis`.

That module did not exist. Every Redis touch from those paths raised
ImportError at runtime, was caught by surrounding try/except, and
fell through to in-memory dicts (`_MEMORY_SNAPSHOTS`,
`_MEMORY_DIRECTIVES`, `_MEMORY_VALIDATED`, etc.). The DCIL pipeline
appeared to "run" but never persisted state across process boundaries
— directives written by task_28 were unreadable by task_29's offline
analysis after a restart.

This module restores the synchronous side. It exposes `get_redis()`
returning either a connected `redis.Redis` (synchronous) client or
None when Redis is unreachable. Callers branch on the None and fall
back to in-memory state — preserving the existing degraded-but-working
behavior, but no longer silently dropping persistence when Redis IS
reachable.

Configuration is read from `adam.config.settings.RedisSettings`,
identical to the async client at `adam/core/dependencies.py:69-79`.
The two clients can coexist; the sync client uses its own connection
pool because the async client's pool is loop-bound and not shareable
across sync code.
"""

from __future__ import annotations

import logging
from typing import Optional

import redis as redis_sync  # synchronous client; the async client lives at adam.core.dependencies

from adam.config.settings import settings

logger = logging.getLogger(__name__)


_SYNC_CLIENT: Optional[redis_sync.Redis] = None
_INIT_ATTEMPTED = False


def get_redis() -> Optional[redis_sync.Redis]:
    """Return a connected synchronous Redis client, or None.

    Lazily initializes a process-singleton client on first call.
    Returns None when Redis is unreachable or unconfigured — callers
    must handle this and fall back to in-memory state.

    Connection failure is surfaced as None (not raised). The first
    failure logs a warning; subsequent calls return None silently to
    avoid log-spam in tight loops.
    """
    global _SYNC_CLIENT, _INIT_ATTEMPTED

    if _SYNC_CLIENT is not None:
        return _SYNC_CLIENT

    if _INIT_ATTEMPTED and _SYNC_CLIENT is None:
        # Already failed once this process; don't re-attempt.
        return None

    _INIT_ATTEMPTED = True

    try:
        cfg = settings.redis
        client = redis_sync.Redis(
            host=cfg.host,
            port=cfg.port,
            password=cfg.password,
            db=cfg.db,
            ssl=cfg.ssl,
            socket_timeout=cfg.socket_timeout,
            socket_connect_timeout=cfg.socket_connect_timeout,
            max_connections=cfg.max_connections,
        )
        client.ping()  # blocking; surfaces auth/connection errors immediately
    except Exception as exc:
        logger.warning("Synchronous Redis client unavailable (%s); callers will fall back to in-memory state", exc)
        return None

    _SYNC_CLIENT = client
    logger.info("Synchronous Redis client connected at %s:%d", cfg.host, cfg.port)
    return _SYNC_CLIENT


def reset_for_tests() -> None:
    """Reset the cached client. Tests should call this between cases that
    differ in Redis configuration. Not for production use.
    """
    global _SYNC_CLIENT, _INIT_ATTEMPTED
    if _SYNC_CLIENT is not None:
        try:
            _SYNC_CLIENT.close()
        except Exception:
            pass
    _SYNC_CLIENT = None
    _INIT_ATTEMPTED = False
