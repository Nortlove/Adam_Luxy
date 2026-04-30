"""Negative-outcome webhook router — Spine #11 end-to-end wire.

POST /api/v1/negative-outcomes/event
    Body: arbitrary JSON dict — adapter registry decides shape.

Flow:
  1. Parse JSON body (any shape).
  2. registry.dispatch(payload) → NormalizedNegativeOutcome | None.
     - None → adapter stack didn't recognize the payload. Returns
       422 with diagnostics so external callers can see their
       payload didn't match anything. The SapidRoundTripMonitor
       (Phase 8) records the resolution failure.
     - NormalizedNegativeOutcome → continue.
  3. OutcomeHandler.process_outcome with normalized fields.
     Foundation §7 rule 11: ethics gate inside process_outcome
     converts known negative outcome_types into magnitude-weighted
     signed_reward against whatever mechanism produced the original
     conversion.

Soft-fail: outcome handler errors are logged but do NOT 500 the
caller — the payload was VALID and ADAPTABLE, the downstream
learning pipeline is the one degraded. We don't punish the upstream
caller (LUXY booking system) by failing their webhook delivery on
our internal degradation.

Authentication: deferred. The default registry is permissive (any
shape that an adapter recognizes). When LUXY confirms HMAC secret
or shared-secret auth, gate the endpoint behind that — don't bake
auth into the adapter layer (the adapter is shape-translation only).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from adam.intelligence.negative_outcome_adapters import get_default_registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/negative-outcomes",
    tags=["negative-outcomes"],
)


_outcome_handler = None


def _get_outcome_handler():
    """Lazy-initialize the OutcomeHandler singleton.

    OutcomeHandler is stateful (counts processed outcomes), so reuse
    one instance across requests. Soft-fails to None on import error
    so the router still answers — the downstream call is wrapped in
    try/except below.
    """
    global _outcome_handler
    if _outcome_handler is None:
        try:
            from adam.core.learning.outcome_handler import OutcomeHandler
            _outcome_handler = OutcomeHandler()
        except Exception as exc:
            logger.warning("OutcomeHandler import failed: %s", exc)
            _outcome_handler = None
    return _outcome_handler


@router.post("/event")
async def receive_negative_outcome(request: Request) -> Dict[str, Any]:
    """Receive a negative-outcome event (any shape) and feed the
    learning loop.

    Returns:
        {
          "status": "processed" | "unrecognized" | "degraded",
          "decision_id": str | None,
          "outcome_type": str | None,
          "source_adapter": str | None,
          "latency_ms": float,
        }
    """
    start = time.monotonic()

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid JSON: {exc}",
        )
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Body must be a JSON object",
        )

    registry = get_default_registry()
    normalized = registry.dispatch(payload)

    if normalized is None:
        # No adapter recognized this payload shape. The
        # SapidRoundTripMonitor already recorded the resolution
        # failure inside registry.dispatch; we surface it back to
        # the caller so they can see the payload didn't match.
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "negative-outcome webhook: unrecognized payload (keys=%s)",
            list(payload.keys())[:8],
        )
        raise HTTPException(
            status_code=422,
            detail={
                "status": "unrecognized",
                "reason": (
                    "no adapter in the registry recognized this payload "
                    "shape. Check adapter source_id list against your "
                    "payload's keys."
                ),
                "payload_keys": list(payload.keys()),
                "latency_ms": round(elapsed_ms, 2),
            },
        )

    handler = _get_outcome_handler()
    if handler is None:
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "status": "degraded",
            "reason": "OutcomeHandler not available; event normalized but not learned",
            "decision_id": normalized.decision_id,
            "outcome_type": normalized.outcome_type,
            "source_adapter": normalized.metadata.get("source_adapter"),
            "latency_ms": round(elapsed_ms, 2),
        }

    try:
        await handler.process_outcome(
            decision_id=normalized.decision_id,
            outcome_type=normalized.outcome_type,
            outcome_value=normalized.outcome_value,
            metadata=normalized.metadata,
        )
    except Exception as exc:
        # Soft-fail: don't punish the upstream caller for our
        # internal learning-pipeline degradation.
        logger.warning(
            "negative-outcome webhook: OutcomeHandler.process_outcome "
            "failed for decision_id=%s outcome_type=%s: %s",
            normalized.decision_id, normalized.outcome_type, exc,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "status": "degraded",
            "reason": f"OutcomeHandler error: {str(exc)[:200]}",
            "decision_id": normalized.decision_id,
            "outcome_type": normalized.outcome_type,
            "source_adapter": normalized.metadata.get("source_adapter"),
            "latency_ms": round(elapsed_ms, 2),
        }

    elapsed_ms = (time.monotonic() - start) * 1000
    return {
        "status": "processed",
        "decision_id": normalized.decision_id,
        "outcome_type": normalized.outcome_type,
        "source_adapter": normalized.metadata.get("source_adapter"),
        "latency_ms": round(elapsed_ms, 2),
    }


@router.get("/adapters")
async def list_adapters() -> Dict[str, Any]:
    """Diagnostic — list registered adapters in dispatch order.

    Useful for ops to verify the LUXY adapter is in front of the
    generic catch-all (which it must be, since the LUXY shape would
    otherwise fall through to GenericJSON if its event_type happened
    to match).
    """
    registry = get_default_registry()
    adapters = [
        getattr(a, "source_id", a.__class__.__name__)
        for a in registry._adapters  # noqa: SLF001 — diagnostic
    ]
    return {
        "count": registry.adapter_count(),
        "dispatch_order": adapters,
    }
