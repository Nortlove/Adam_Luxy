# =============================================================================
# Nonconscious Signal Intelligence — API Router
# Location: adam/api/signals/router.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 1
# =============================================================================

"""
API endpoints for site telemetry ingestion and signal profile retrieval.

POST /api/v1/signals/session    — Receive telemetry payload from INFORMATIV JS
GET  /api/v1/signals/user/{id}  — Retrieve accumulated signal profile
GET  /api/v1/signals/population — Population-level baselines
GET  /api/v1/signals/health     — Signal collection health check
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from adam.retargeting.models.telemetry import (
    StoredSignalProfile,
    TelemetrySessionPayload,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/signals",
    tags=["nonconscious-signals"],
)


# =============================================================================
# DEPENDENCY: Signal Collector singleton
# =============================================================================

def _get_signal_collector():
    """Get the platform-managed NonconsciousSignalCollector singleton."""
    try:
        from adam.core.dependencies import LearningComponents, Infrastructure

        infra = Infrastructure.get_instance()
        components = LearningComponents.get_instance(infra)
        collector = components.signal_collector
        if collector is not None:
            return collector
    except Exception:
        pass

    # Fallback: create a local instance for dev/testing
    try:
        from adam.core.dependencies import Infrastructure
        from adam.retargeting.engines.signal_collector import NonconsciousSignalCollector

        infra = Infrastructure.get_instance()
        return NonconsciousSignalCollector(redis_client=infra.redis)
    except Exception as e:
        logger.error("Cannot create signal collector: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Signal collection service unavailable",
        )


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class SessionIngestResponse(BaseModel):
    status: str
    session_id: str
    visitor_id: Optional[str] = None
    total_sessions: Optional[int] = None
    is_organic: Optional[bool] = None
    sections_recorded: Optional[int] = None
    pages_visited: Optional[int] = None
    latency_ms: float = 0.0


class PopulationBaselines(BaseModel):
    organic_ratio: float = Field(
        ..., description="Population-level organic visit ratio"
    )
    ctr: float = Field(
        ..., description="Population-level click-through rate"
    )


class SignalHealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "34.1"
    components: Dict[str, str] = Field(default_factory=dict)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/session", response_model=SessionIngestResponse)
async def ingest_telemetry_session(
    payload: TelemetrySessionPayload,
    collector=Depends(_get_signal_collector),
):
    """Receive a telemetry session payload from the INFORMATIV JS script.

    Called at session end (beforeunload/visibilitychange) from the
    advertiser's site. Idempotent — duplicate session_ids are rejected.
    Target latency: <50ms.
    """
    start = time.monotonic()
    result = await collector.ingest_session(payload)
    elapsed_ms = (time.monotonic() - start) * 1000

    return SessionIngestResponse(
        **result,
        latency_ms=round(elapsed_ms, 2),
    )


@router.get("/user/{user_id}", response_model=StoredSignalProfile)
async def get_signal_profile(
    user_id: str,
    collector=Depends(_get_signal_collector),
):
    """Retrieve the accumulated nonconscious signal profile for a user.

    Returns the full StoredSignalProfile with all signal data
    accumulated across sessions. Used by the DiagnosticReasoner
    and retargeting planner.
    """
    profile = await collector.get_profile(user_id)
    if profile is None or profile.total_sessions == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No signal profile found for user {user_id}",
        )
    return profile


@router.get("/user/{user_id}/nonconscious-profile")
async def get_nonconscious_profile(
    user_id: str,
    mechanism: str = "",
    device: str = "",
    collector=Depends(_get_signal_collector),
):
    """Get the composite NonconsciousProfile with aggregate H-modifiers.

    This is the decision-ready view of all 6 signals for one user.
    Pass optional mechanism/device to compute device-mechanism compatibility.

    Returns the full profile dict including aggregate_h_modifiers and
    mechanism_override recommendation.
    """
    stored = await collector.get_profile(user_id)
    if stored is None or stored.total_sessions == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No signal profile found for user {user_id}",
        )

    from adam.retargeting.engines.nonconscious_profile import build_from_stored_profile
    profile = build_from_stored_profile(stored, mechanism, device)
    return profile.to_dict()


@router.get("/population", response_model=PopulationBaselines)
async def get_population_baselines(
    collector=Depends(_get_signal_collector),
):
    """Get population-level signal baselines.

    Used by Signal 3 (organic return surge detection) and
    Signal 6 (frequency decay / population CTR).
    """
    return PopulationBaselines(
        organic_ratio=await collector.get_population_organic_ratio(),
        ctr=await collector.get_population_ctr(),
    )


@router.get("/health", response_model=SignalHealthResponse)
async def signal_health():
    """Health check for the nonconscious signal collection subsystem."""
    components = {}

    try:
        collector = _get_signal_collector()
        components["collector"] = "available"
    except Exception:
        components["collector"] = "unavailable"

    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        await infra.redis.ping()
        components["redis"] = "connected"
    except Exception:
        components["redis"] = "disconnected"

    all_healthy = all(
        v in ("available", "connected") for v in components.values()
    )

    return SignalHealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="34.1",
        components=components,
    )
