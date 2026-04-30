# =============================================================================
# Spine #6 — DecisionTrace Redis hot-cache storage substrate
# Location: adam/intelligence/decision_trace_store.py
# =============================================================================
"""Redis hot-cache storage for ``DecisionTrace`` records.

Closes the Redis half of directive Spine #6 line 248:

    "Hot trace cache in Redis (TTL matched to demo loop, e.g., 7-30
     days). Long-term archival in Neo4j as DecisionTrace nodes linked
     to the User, the ConversionEdge (when the impression resolves),
     and the Mechanism."

This slice ships the Redis substrate. Long-term Neo4j archival is the
sibling slice that composes on top.

WHY THIS EXISTS
---------------

The ``DecisionTrace`` schema (adam/intelligence/decision_trace.py,
shipped ca03336) is the data contract. Without a write path, traces
get built and discarded — exactly the "measurement without immediate
decision-time consumer" antipattern Appendix E rule A flags. This
module is the consumer: every trace produced at decision time gets
written here; every read from the Defensive Reasoning renderer reads
from here.

KEY SCHEMA
----------

  decision_trace:{decision_id}              → JSON-serialized trace
  decision_trace_user_idx:{user_id}         → Redis list of
                                              decision_ids (newest
                                              pushed to head)

The user index lets the Defensive Reasoning surface answer "show me
this user's recent decisions" without requiring a Neo4j query path
in the hot loop. Index TTL is longer than primary TTL so the index
doesn't expire ahead of the records it points at; missing primaries
during fan-out are silently skipped (the trace TTL'd out faster than
the index entry).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: directive Spine #6 line 248. Standard Redis TTL +
    list-as-secondary-index pattern. Pydantic v2
    model_dump_json/model_validate_json for the serialization
    contract.

(b) Tests pin: round-trip via fake async Redis preserves trace;
    TTL set on store; missing decision_id → load returns None;
    soft-fail on missing client; user index returns most-recent
    traces; bad JSON in Redis → load returns None (not raises);
    multiple traces same user retrievable; index list trim discipline
    (max 1000 ids per user).

(c) calibration_pending=True. TTL defaults are conservative (14 days
    for primary, 30 days for index — within directive's 7-30 day
    band). LUXY pilot will calibrate against actual demo-loop
    latency. A14 flag: SPINE_6_DECISION_TRACE_TTL_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Neo4j long-term archival (:DecisionTrace nodes linked to
      :User, :ConversionEdge, :Mechanism per directive line 248) —
      sibling slice.
    * Producer wiring: bilateral_cascade.py call site that builds
      and stores the trace at decision time — sibling slice.
    * Defensive Reasoning renderer (Spine #13) reading from these
      stored traces — its own slice.
    * Cypher query "show me all decisions for this user this week"
      (directive line 248) — needs Neo4j archival; covered by the
      sibling slice's substrate.
    * Cross-region replication / cold-storage migration — out of
      scope for the hot-cache substrate.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from adam.intelligence.decision_trace import DecisionTrace

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending TTLs + key prefixes
# =============================================================================

# A14 SPINE_6_DECISION_TRACE_TTL_PILOT_PENDING
#
# Within directive's 7-30 day band. Defaults set conservatively;
# pilot data will calibrate (longer if DR rendering frequency is
# high; shorter if Redis pressure dominates).

DEFAULT_TRACE_TTL_SECONDS: int = 14 * 86400        # 14 days
USER_INDEX_TTL_SECONDS: int = 30 * 86400           # 30 days (>= primary)

# Key prefixes
_PRIMARY_KEY_PREFIX: str = "decision_trace:"
_USER_INDEX_PREFIX: str = "decision_trace_user_idx:"

# Per-user index list cap. Beyond this, oldest decision_ids are
# trimmed from the tail. 1000 is generous for any demo-loop window
# at LUXY scale; protects the index against unbounded growth.
USER_INDEX_MAX_LENGTH: int = 1000


# =============================================================================
# Key builders (kept module-level so tests can pin the schema)
# =============================================================================


def primary_key(decision_id: str) -> str:
    """Return the Redis key for the primary trace record."""
    return f"{_PRIMARY_KEY_PREFIX}{decision_id}"


def user_index_key(user_id: str) -> str:
    """Return the Redis key for a user's decision_id index list."""
    return f"{_USER_INDEX_PREFIX}{user_id}"


# =============================================================================
# Store
# =============================================================================


async def store_trace(
    trace: DecisionTrace,
    redis_client: Optional[Any],
    *,
    ttl_seconds: int = DEFAULT_TRACE_TTL_SECONDS,
) -> bool:
    """Persist a ``DecisionTrace`` to Redis with TTL.

    Args:
        trace: the trace to store. ``trace.decision_id`` and
            ``trace.user_id`` are load-bearing.
        redis_client: an async Redis client (e.g.
            ``redis.asyncio.Redis``). When ``None``, the function
            soft-fails to ``False`` — the caller should not have to
            check the client itself.
        ttl_seconds: primary record TTL. Defaults to
            DEFAULT_TRACE_TTL_SECONDS (14 days).

    Returns:
        True on successful primary write. The user-index update is
        best-effort: a successful primary with a failed index update
        still returns True (the trace is reachable via direct
        decision_id; index loss only affects "list by user" queries).

    Soft-fail discipline:
      * No client → False, log debug.
      * Redis exception during primary set → False, log warning.
      * Redis exception during index update → True, log warning.
        Primary already wrote; the index loss is recoverable.
      * Trace serialization exception → False, log warning. Should
        never happen — DecisionTrace is Pydantic-typed — but defensive.
    """
    if redis_client is None:
        logger.debug(
            "store_trace: no redis client (soft-fail to False)"
        )
        return False

    try:
        payload = trace.model_dump_json()
    except Exception as exc:
        logger.warning(
            "store_trace serialization failed for decision_id=%s: %s",
            trace.decision_id, exc,
        )
        return False

    pkey = primary_key(trace.decision_id)
    try:
        await redis_client.set(pkey, payload, ex=int(ttl_seconds))
    except Exception as exc:
        logger.warning(
            "store_trace primary write failed for decision_id=%s: %s",
            trace.decision_id, exc,
        )
        return False

    # User index — best-effort. Push to head so newest decisions
    # come back first; trim to USER_INDEX_MAX_LENGTH; refresh TTL.
    if trace.user_id:
        ikey = user_index_key(trace.user_id)
        try:
            await redis_client.lpush(ikey, trace.decision_id)
            await redis_client.ltrim(ikey, 0, USER_INDEX_MAX_LENGTH - 1)
            await redis_client.expire(ikey, int(USER_INDEX_TTL_SECONDS))
        except Exception as exc:
            logger.warning(
                "store_trace user index update failed for user=%s "
                "decision_id=%s: %s (primary still written)",
                trace.user_id, trace.decision_id, exc,
            )

    return True


# =============================================================================
# Load
# =============================================================================


async def load_trace(
    decision_id: str,
    redis_client: Optional[Any],
) -> Optional[DecisionTrace]:
    """Fetch a single ``DecisionTrace`` by decision_id.

    Returns ``None`` when:
      * redis_client is None
      * Redis read fails (logged at WARNING)
      * key not found (TTL expired or never written)
      * stored payload fails to parse as DecisionTrace (logged)

    The function never raises — Defensive Reasoning rendering paths
    expect a None for "not available" and handle it gracefully.
    """
    if redis_client is None:
        return None

    pkey = primary_key(decision_id)
    try:
        raw = await redis_client.get(pkey)
    except Exception as exc:
        logger.warning(
            "load_trace read failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return None

    if raw is None:
        return None

    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return DecisionTrace.model_validate_json(raw)
    except Exception as exc:
        logger.warning(
            "load_trace parse failed for decision_id=%s: %s",
            decision_id, exc,
        )
        return None


# =============================================================================
# List by user
# =============================================================================


async def list_traces_for_user(
    user_id: str,
    redis_client: Optional[Any],
    *,
    limit: int = 100,
) -> List[DecisionTrace]:
    """Fetch the user's recent traces in newest-first order.

    Reads the user index list, then fan-out fetches each trace.
    Missing primaries (e.g., TTL'd out faster than the index) are
    silently skipped — the index lifespan exceeds the primary TTL by
    design but not always by enough to outlast every record.

    Args:
        user_id: the user whose traces to list.
        redis_client: async Redis client; None → empty list.
        limit: maximum number of traces to return. Capped at
            USER_INDEX_MAX_LENGTH so the function can never read
            beyond the index list's retention.

    Returns: list of ``DecisionTrace``, newest-first. Empty when no
    matches or any redis exception (logged at WARNING).
    """
    if redis_client is None:
        return []
    if limit <= 0:
        return []

    capped_limit = min(int(limit), USER_INDEX_MAX_LENGTH)
    ikey = user_index_key(user_id)

    try:
        decision_ids = await redis_client.lrange(ikey, 0, capped_limit - 1)
    except Exception as exc:
        logger.warning(
            "list_traces_for_user index read failed for user=%s: %s",
            user_id, exc,
        )
        return []

    if not decision_ids:
        return []

    traces: List[DecisionTrace] = []
    for did in decision_ids:
        if isinstance(did, (bytes, bytearray)):
            did = did.decode("utf-8")
        trace = await load_trace(str(did), redis_client)
        if trace is not None:
            traces.append(trace)

    return traces
