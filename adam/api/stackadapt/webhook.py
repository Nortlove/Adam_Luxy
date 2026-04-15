"""
StackAdapt Outcome Webhook — Closes the Learning Loop
========================================================

Receives conversion events from StackAdapt's Pixel API (server-to-server)
and routes them to ADAM's OutcomeHandler, which updates all 10 learning systems:

    1. Thompson Sampling posteriors
    2. Meta-orchestrator strategy weights
    3. Neo4j outcome attribution
    4. Graph rewriter rule effectiveness
    5. Unified Learning Hub (all 30 atoms)
    6. ML ensemble weights
    7. Theory Learner (construct-level)
    8. DSP impression learning
    9. Cognitive learning system
    10. Buyer uncertainty profiles (information value bidding)

Endpoint: POST /api/v1/stackadapt/webhook/conversion
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from adam.api.stackadapt.decision_cache import get_decision_cache
from adam.config.settings import get_settings
from adam.integrations.stackadapt.outcome_mapper import map_stackadapt_event

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/api/v1/stackadapt/webhook", tags=["stackadapt-webhook"])

_outcome_handler = None
_events_received = 0
_events_processed = 0
_events_skipped = 0


# ---------------------------------------------------------------------------
# Event ID deduplication — Redis-backed for production, in-memory fallback
# for development only.
#
# Why Redis: duplicate events that pass the dedup check produce double
# posterior updates in the outcome handler, which systematically biases
# the fitness landscape toward whatever mechanism fired twice. This is
# the same class of failure as the Risk #1 simulation fallback — it
# corrupts the learning loop silently. In-memory dedup is per-pod and
# has no TTL, so under horizontal scale or sustained event volume it
# cannot catch all duplicates. Redis with TTL equal to the upstream
# retry window is the correct structure.
#
# The in-memory fallback is preserved for local development ONLY. In
# production, if Redis is unreachable, the webhook refuses requests
# rather than silently degrading to unreliable per-pod dedup.
# ---------------------------------------------------------------------------


class _LRUSet:
    """Bounded set that evicts the oldest entry when full.

    In-memory dedup fallback for local development only. Per-pod state,
    no TTL, no persistence. Must not be used in production — Redis is
    the correct storage and `_check_duplicate_redis` is the production
    path.
    """

    def __init__(self, maxsize: int = 10_000):
        self._store: OrderedDict[str, None] = OrderedDict()
        self._maxsize = maxsize

    def __contains__(self, key: str) -> bool:
        if key in self._store:
            self._store.move_to_end(key)
            return True
        return False

    def add(self, key: str) -> None:
        if key in self._store:
            self._store.move_to_end(key)
            return
        if len(self._store) >= self._maxsize:
            self._store.popitem(last=False)
        self._store[key] = None


_seen_event_ids_inmem_fallback = _LRUSet(10_000)
_warned_about_inmem_fallback = False


# ---------------------------------------------------------------------------
# HMAC-SHA256 signature validation
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Validate HMAC-SHA256 signature against the raw request body."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _validate_request(request: Request) -> Optional[JSONResponse]:
    """Validate webhook signature. Signature is ALWAYS required.

    Refuses to process if no webhook secret is configured, in any
    environment. An unauthenticated webhook accepts crafted outcomes
    that can be used to manipulate the learning loop's fitness
    function — that is a security failure, not a dev-convenience
    feature. See ADAM_THEORETICAL_FOUNDATION Section 7 rule #11.

    Returns a JSONResponse if the request should be short-circuited,
    or None if processing should continue.
    """
    settings = get_settings()
    secret = settings.stackadapt.webhook_secret

    if not secret:
        mode = "production" if settings.is_production else "development"
        logger.error(
            "Webhook request refused: STACKADAPT_WEBHOOK_SECRET is not "
            "configured (environment=%s). Unauthenticated webhook requests "
            "would accept crafted outcomes that contaminate the learning "
            "loop. Set STACKADAPT_WEBHOOK_SECRET in the environment to "
            "enable the endpoint.",
            mode,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "webhook_secret_not_configured",
                "detail": (
                    "STACKADAPT_WEBHOOK_SECRET must be set in the "
                    "environment. The endpoint refuses requests without "
                    "a configured secret in all environments."
                ),
            },
        )

    signature = request.headers.get("X-Informativ-Signature", "")
    if not signature:
        return JSONResponse(
            status_code=401,
            content={"error": "Missing X-Informativ-Signature header"},
        )
    body = await request.body()
    if not _verify_signature(body, signature, secret):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid signature"},
        )

    return None


async def _check_duplicate(event_id: str) -> Optional[JSONResponse]:
    """Atomically check-and-mark an event_id as seen. Redis first,
    in-memory fallback only in development.

    Uses Redis `SET key value NX EX ttl` for the atomic check-and-mark.
    If the key already existed, the SET returns falsy and the request
    is treated as a duplicate. Otherwise the key is set with an
    expiration equal to `webhook_dedup_ttl_seconds` (default 48 hours).

    If Redis is unreachable AND the environment is development, falls
    back to an in-memory LRU with a loud one-time warning. If Redis is
    unreachable in production, refuses the request rather than
    degrading silently — double-counted outcomes corrupt the learning
    loop and are not recoverable from logs.
    """
    if not event_id:
        return None

    settings = get_settings()

    # --- Try Redis first ---
    try:
        from adam.core.dependencies import get_infrastructure
        infra = await get_infrastructure()
        redis_client = infra.redis
        key = f"{settings.stackadapt.webhook_dedup_key_prefix}{event_id}"
        set_result = await redis_client.set(
            key,
            "1",
            nx=True,
            ex=settings.stackadapt.webhook_dedup_ttl_seconds,
        )
        # redis-py returns True on successful SET, None when NX prevents
        # the set (i.e. the key already existed → duplicate).
        if set_result is None or set_result is False:
            return JSONResponse(
                status_code=200,
                content={"status": "duplicate", "skipped": True, "dedup_store": "redis"},
            )
        return None
    except Exception as exc:
        if settings.is_production:
            logger.error(
                "Webhook dedup refused: Redis unreachable in production "
                "(event_id=%s, error=%s). Accepting the request without "
                "persistent dedup would allow double posterior updates "
                "from duplicate deliveries. Refusing instead.",
                event_id, exc,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "dedup_store_unavailable",
                    "detail": (
                        "Redis is not reachable and in-memory dedup is "
                        "not safe in production. The webhook will resume "
                        "accepting requests once Redis is healthy."
                    ),
                },
            )

        # Development-only fallback: warn loudly once, then use the
        # bounded in-memory LRU. Per-pod state, no TTL — must not be
        # used in production.
        global _warned_about_inmem_fallback
        if not _warned_about_inmem_fallback:
            logger.warning(
                "Webhook dedup falling back to in-memory LRU (per-pod, "
                "no TTL). This mode is ONLY safe for local development. "
                "Redis error: %s",
                exc,
            )
            _warned_about_inmem_fallback = True

        if event_id in _seen_event_ids_inmem_fallback:
            return JSONResponse(
                status_code=200,
                content={"status": "duplicate", "skipped": True, "dedup_store": "memory"},
            )
        _seen_event_ids_inmem_fallback.add(event_id)
        return None


def _get_outcome_handler():
    global _outcome_handler
    if _outcome_handler is None:
        try:
            from adam.core.learning.outcome_handler import OutcomeHandler
            _outcome_handler = OutcomeHandler()
        except ImportError:
            logger.warning("OutcomeHandler not available")
    return _outcome_handler


async def _lookup_decision_context_neo4j(decision_id: str):
    """Try to recover a DecisionContext from Neo4j durable storage.

    This covers the case where the app restarted between decision and
    outcome, so the in-memory cache was lost.
    """
    try:
        from adam.core.dependencies import get_infrastructure
        from adam.api.stackadapt.decision_cache import DecisionContext
        import json

        infra = get_infrastructure()
        driver = getattr(infra, "neo4j_driver", None) if infra else None
        if not driver:
            return None

        async with driver.session() as session:
            result = await session.run(
                "MATCH (dc:DecisionContext {decision_id: $did}) RETURN dc LIMIT 1",
                did=decision_id,
            )
            record = await result.single()
            if not record:
                return None

            node = record["dc"]
            metadata_json = node.get("metadata_json", "")
            if not metadata_json:
                # Minimal context from node properties
                return DecisionContext(
                    decision_id=decision_id,
                    archetype=node.get("archetype", ""),
                    mechanism_sent=node.get("mechanism_sent", ""),
                    cascade_level=node.get("cascade_level", 1),
                    buyer_id=node.get("buyer_id", ""),
                    segment_id=node.get("segment_id", ""),
                    created_at=node.get("created_at", time.time()),
                )

            # Full context from serialized metadata
            meta = json.loads(metadata_json)
            return DecisionContext(
                decision_id=decision_id,
                archetype=meta.get("archetype", ""),
                mechanism_sent=meta.get("mechanism_sent", ""),
                secondary_mechanism=meta.get("secondary_mechanism", ""),
                mechanisms_considered=meta.get("mechanisms_considered", []),
                cascade_level=meta.get("cascade_level", 1),
                evidence_source=meta.get("evidence_source", ""),
                edge_dimensions=meta.get("alignment_scores", {}),
                mechanism_scores=meta.get("mechanism_scores", {}),
                framing=meta.get("framing", "mixed"),
                ndf_profile=meta.get("ndf_profile", {}),
                segment_id=meta.get("segment_id", ""),
                asin=meta.get("asin", ""),
                buyer_id=meta.get("buyer_id", ""),
                product_category=meta.get("product_category", ""),
                content_category=meta.get("content_category", ""),
                gradient_priorities=meta.get("gradient_priorities", []),
                information_value=meta.get("information_value_at_decision", 0.0),
                buyer_confidence=meta.get("buyer_confidence_at_decision", 0.0),
                barrier_diagnosed=meta.get("barrier_diagnosed", ""),
                therapeutic_mechanism=meta.get("therapeutic_mechanism", ""),
                sequence_id=meta.get("sequence_id", ""),
                touch_position=meta.get("touch_position", 0),
                scaffold_level=meta.get("scaffold_level", 0),
                conversion_stage=meta.get("conversion_stage", ""),
                created_at=meta.get("decision_timestamp", time.time()),
            )
    except Exception as e:
        logger.debug("Neo4j decision context lookup failed: %s", e)
        return None


class PixelEvent(BaseModel):
    """A StackAdapt pixel event received server-to-server."""

    event_id: str = Field(default="", description="Unique event identifier for deduplication")
    uid: str = Field(default="", description="StackAdapt universal pixel ID")
    url: str = Field(default="", description="Page URL where conversion occurred")
    user_agent: str = Field(default="")
    user_ip: str = Field(default="")
    page_title: str = Field(default="")
    event_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload: action, revenue, order_id, informativ_segment_id",
    )


class BatchPixelEvents(BaseModel):
    """Batch of pixel events for bulk processing."""

    events: List[PixelEvent]


class WebhookResponse(BaseModel):
    """Response from processing conversion events."""

    received: int
    processed: int
    skipped: int
    updates: Dict[str, Any] = {}


class WebhookHealthResponse(BaseModel):
    """Webhook health metrics."""

    status: str
    total_received: int
    total_processed: int
    total_skipped: int
    outcome_handler_available: bool
    decision_cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Decision cache stats: size, hit rate, etc.",
    )


@webhook_router.post(
    "/conversion",
    response_model=WebhookResponse,
    summary="Receive StackAdapt conversion event",
    description="Receives a conversion event from StackAdapt Pixel API and routes to all 10 learning systems.",
)
async def receive_conversion(request: Request, event: PixelEvent):
    global _events_received, _events_processed, _events_skipped

    # Signature validation
    auth_response = await _validate_request(request)
    if auth_response is not None:
        return auth_response

    # Deduplication (Redis-backed; dev-only in-memory fallback inside)
    dup_response = await _check_duplicate(event.event_id)
    if dup_response is not None:
        return dup_response

    _events_received += 1

    mapped = map_stackadapt_event(event.model_dump())
    if not mapped:
        _events_skipped += 1
        return WebhookResponse(received=1, processed=0, skipped=1)

    # ──────────────────────────────────────────────────────────────────
    # RETRIEVE DECISION CONTEXT from the cache.
    #
    # This is the critical link: the webhook event carries minimal info
    # (segment_id, revenue, action). The decision cache has the FULL
    # context from decision time (archetype, mechanism_sent, cascade_level,
    # alignment scores, buyer_id, gradient priorities).
    #
    # Without this, the outcome handler credits the wrong mechanisms,
    # updates the wrong Thompson Sampling cells, and can't update the
    # buyer profile at all.
    # ──────────────────────────────────────────────────────────────────
    metadata = mapped["metadata"]
    decision_cache = get_decision_cache()

    # Try 1: decision_id echoed back by StackAdapt in event_args
    decision_id = (
        event.event_args.get("decision_id")
        or mapped["decision_id"]
    )
    decision_ctx = decision_cache.retrieve(decision_id)

    # Try 2: fallback lookup by buyer + segment (for cases where
    # StackAdapt doesn't echo the decision_id)
    if decision_ctx is None:
        buyer_id = metadata.get("buyer_id", "")
        segment_id = metadata.get("segment_id", "")
        if buyer_id and segment_id:
            decision_ctx = decision_cache.lookup_by_buyer_segment(buyer_id, segment_id)

    # Try 3: Neo4j durable fallback (covers app restarts between
    # decision and outcome — decisions persist beyond in-memory TTL)
    if decision_ctx is None and decision_id:
        decision_ctx = await _lookup_decision_context_neo4j(decision_id)
        if decision_ctx:
            logger.info(
                "Decision context recovered from Neo4j: id=%s", decision_id,
            )

    # Merge decision-time context into metadata
    if decision_ctx is not None:
        decision_metadata = decision_ctx.to_outcome_metadata()
        # Decision-time values override webhook-inferred values
        metadata.update(decision_metadata)
        metadata["decision_context_found"] = True
        metadata["decision_latency_seconds"] = round(
            time.time() - decision_ctx.created_at, 1
        )
        logger.info(
            "Decision context found: id=%s arch=%s mech=%s level=%d delay=%.0fs",
            decision_ctx.decision_id,
            decision_ctx.archetype,
            decision_ctx.mechanism_sent,
            decision_ctx.cascade_level,
            time.time() - decision_ctx.created_at,
        )
    else:
        metadata["decision_context_found"] = False
        logger.error(
            "Decision context NOT found in cache or Neo4j for decision_id=%s — "
            "Thompson update will credit wrong mechanism, gradient learning degraded. "
            "This outcome's learning value is severely reduced.",
            decision_id,
        )

    handler = _get_outcome_handler()
    updates = {}
    if handler:
        try:
            result = await handler.process_outcome(
                decision_id=decision_id,
                outcome_type=mapped["outcome_type"],
                outcome_value=mapped["outcome_value"],
                metadata=metadata,
            )
            updates = result.get("updates", {})
            updates["decision_context_found"] = metadata["decision_context_found"]
            _events_processed += 1
        except Exception as e:
            logger.error("Outcome processing failed: %s", e)
            _events_skipped += 1
            return WebhookResponse(received=1, processed=0, skipped=1, updates={"error": str(e)})
    else:
        _events_skipped += 1
        logger.warning("OutcomeHandler not available; event logged but not processed")

    return WebhookResponse(received=1, processed=1, skipped=0, updates=updates)


@webhook_router.post(
    "/conversion/batch",
    response_model=WebhookResponse,
    summary="Batch receive StackAdapt conversion events",
    description="Process multiple conversion events in a single request.",
)
async def receive_conversions_batch(request: Request, batch: BatchPixelEvents):
    global _events_received, _events_processed, _events_skipped

    # Signature validation
    auth_response = await _validate_request(request)
    if auth_response is not None:
        return auth_response

    total_received = len(batch.events)
    total_processed = 0
    total_skipped = 0
    all_updates: Dict[str, Any] = {}

    handler = _get_outcome_handler()
    # Bug fix (2026-04-15): `decision_cache` was previously referenced
    # inside this function without being defined, raising NameError on
    # the first event. The single-event endpoint defines it locally on
    # line ~304; the batch endpoint did not. The batch endpoint has
    # never worked. Defining it here makes it work.
    decision_cache = get_decision_cache()

    for event in batch.events:
        # Per-event deduplication (Redis-backed; dev-only in-memory fallback inside)
        dup_response = await _check_duplicate(event.event_id)
        if dup_response is not None:
            total_skipped += 1
            _events_skipped += 1
            continue

        _events_received += 1
        mapped = map_stackadapt_event(event.model_dump())

        if not mapped:
            total_skipped += 1
            _events_skipped += 1
            continue

        # Enrich metadata with decision context (same logic as single endpoint)
        metadata = mapped["metadata"]
        decision_id = event.event_args.get("decision_id") or mapped["decision_id"]
        decision_ctx = decision_cache.retrieve(decision_id)
        if decision_ctx is None:
            buyer_id = metadata.get("buyer_id", "")
            segment_id = metadata.get("segment_id", "")
            if buyer_id and segment_id:
                decision_ctx = decision_cache.lookup_by_buyer_segment(buyer_id, segment_id)
        if decision_ctx is not None:
            metadata.update(decision_ctx.to_outcome_metadata())
            metadata["decision_context_found"] = True
        else:
            metadata["decision_context_found"] = False

        if handler:
            try:
                result = await handler.process_outcome(
                    decision_id=decision_id,
                    outcome_type=mapped["outcome_type"],
                    outcome_value=mapped["outcome_value"],
                    metadata=metadata,
                )
                total_processed += 1
                _events_processed += 1
            except Exception as e:
                logger.warning("Batch outcome processing failed for %s: %s", decision_id, e)
                total_skipped += 1
                _events_skipped += 1
        else:
            total_skipped += 1
            _events_skipped += 1

    all_updates["batch_size"] = total_received
    all_updates["processed"] = total_processed

    return WebhookResponse(
        received=total_received,
        processed=total_processed,
        skipped=total_skipped,
        updates=all_updates,
    )


@webhook_router.get(
    "/health",
    response_model=WebhookHealthResponse,
    summary="Webhook health and metrics",
)
async def webhook_health():
    handler = _get_outcome_handler()
    cache = get_decision_cache()
    return WebhookHealthResponse(
        status="healthy",
        total_received=_events_received,
        total_processed=_events_processed,
        total_skipped=_events_skipped,
        outcome_handler_available=handler is not None,
        decision_cache=cache.stats,
    )
